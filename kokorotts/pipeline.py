from .catalog import DEFAULT_MODEL_REPO_ID, LANGUAGE_ALIASES, PIPELINE_LANGUAGE_CODES
from .english_pronunciation import correct_english_pronunciations
from .model import KModel
from .text_normalization import normalize_english_text
from dataclasses import dataclass
from huggingface_hub import hf_hub_download
from loguru import logger
from misaki import en, espeak
from typing import Callable, Generator, List, Optional, Tuple, Union
import re
import torch
import os

ALIASES = LANGUAGE_ALIASES
LANG_CODES = PIPELINE_LANGUAGE_CODES
MODEL_PHONEME_LIMIT = 510
ENGLISH_QUALITY_PHONEME_LIMIT = 400


class KPipeline:
    '''
    KPipeline is a language-aware support class with 2 main responsibilities:
    1. Perform language-specific G2P, mapping (and chunking) text -> phonemes
    2. Manage and store voices, lazily downloaded from HF if needed

    You are expected to have one KPipeline per language. If you have multiple
    KPipelines, you should reuse one KModel instance across all of them.

    KPipeline is designed to work with a KModel, but this is not required.
    There are 2 ways to pass an existing model into a pipeline:
    1. On init: us_pipeline = KPipeline(lang_code='a', model=model)
    2. On call: us_pipeline(text, voice, model=model)

    By default, KPipeline will automatically initialize its own KModel. To
    suppress this, construct a "quiet" KPipeline with model=False.

    A "quiet" KPipeline yields (graphemes, phonemes, None) without generating
    any audio. You can use this to phonemize and chunk your text in advance.

    A "loud" KPipeline _with_ a model yields (graphemes, phonemes, audio).
    '''
    def __init__(
        self,
        lang_code: str,
        repo_id: Optional[str] = None,
        model: Union[KModel, bool] = True,
        trf: bool = False,
        en_callable: Optional[Callable[[str], str]] = None,
        device: Optional[str] = None
    ):
        """Initialize a KPipeline.
        
        Args:
            lang_code: Language code for G2P processing
            model: KModel instance, True to create new model, False for no model
            trf: Whether to use transformer-based G2P
            device: Override default device selection ('cuda' or 'cpu', or None for auto)
                   If None, will auto-select cuda if available
                   If 'cuda' and not available, will explicitly raise an error
        """
        if repo_id is None:
            repo_id = DEFAULT_MODEL_REPO_ID
            print(f"WARNING: Defaulting repo_id to {repo_id}. Pass repo_id='{repo_id}' to suppress this warning.")
        self.repo_id = repo_id
        lang_code = lang_code.lower()
        lang_code = ALIASES.get(lang_code, lang_code)
        assert lang_code in LANG_CODES, (lang_code, LANG_CODES)
        self.lang_code = lang_code
        self.model = None
        if isinstance(model, KModel):
            self.model = model
        elif model:
            if device == 'cuda' and not torch.cuda.is_available():
                raise RuntimeError("CUDA requested but not available")
            if device == 'mps' and not torch.backends.mps.is_available():
                raise RuntimeError("MPS requested but not available")
            if device == 'mps' and os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') != '1':
                raise RuntimeError("MPS requested but fallback not enabled")
            if device is None:
                if torch.cuda.is_available():
                    device = 'cuda'
                elif os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1' and torch.backends.mps.is_available():
                    device = 'mps'
                else:
                    device = 'cpu'
            try:
                self.model = KModel(repo_id=repo_id).to(device).eval()
            except RuntimeError as e:
                if device == 'cuda':
                    raise RuntimeError(f"""Failed to initialize model on CUDA: {e}. 
                                       Try setting device='cpu' or check CUDA installation.""")
                raise
        self.voices = {}
        if lang_code in 'ab':
            try:
                fallback = espeak.EspeakFallback(british=lang_code=='b')
            except Exception as e:
                logger.warning("EspeakFallback not Enabled: OOD words will be skipped")
                logger.warning({str(e)})
                fallback = None
            self.g2p = en.G2P(trf=trf, british=lang_code=='b', fallback=fallback, unk='')
        elif lang_code == 'j':
            try:
                from misaki import ja
                self.g2p = ja.JAG2P(version='pyopenjtalk')
            except ImportError:
                logger.error("You need to install pyopenjtalk to use lang_code='j'")
                raise
        elif lang_code == 'z':
            try:
                from misaki import zh
                self.g2p = zh.ZHG2P(
                    version=None if repo_id.endswith('/Kokoro-82M') else '1.1',
                    en_callable=en_callable
                )
            except ImportError:
                logger.error("You need to `pip install misaki[zh]` to use lang_code='z'")
                raise
        elif lang_code == 'd':
            try:
                from misaki import de
                self.g2p = de.DEG2P()
            except ImportError:
                logger.error("You need to `pip install misaki[de]` to use lang_code='d'")
                raise
        elif lang_code == 'v':
            try:
                from vig2p import phonemize_text
            except ImportError:
                logger.error("You need to `pip install vig2p` to use lang_code='v'")
                raise

            def vietnamese_g2p(text: str):
                return phonemize_text(text), None

            self.g2p = vietnamese_g2p
        else:
            language = LANG_CODES[lang_code]
            self.g2p = espeak.EspeakG2P(language=language)

    def load_single_voice(self, voice: str):
        if voice in self.voices:
            return self.voices[voice]
        if voice.endswith('.pt'):
            f = voice
        else:
            f = hf_hub_download(repo_id=self.repo_id, filename=f'voices/{voice}.pt')
            if not voice.startswith(self.lang_code):
                v = LANG_CODES.get(voice, voice)
                p = LANG_CODES.get(self.lang_code, self.lang_code)
                logger.warning(f'Language mismatch, loading {v} voice into {p} pipeline.')
        pack = torch.load(f, weights_only=True)
        self.voices[voice] = pack
        return pack

    """
    load_voice is a helper function that lazily downloads and loads a voice:
    Single voice can be requested (e.g. 'af_bella') or multiple voices (e.g. 'af_bella,af_jessica').
    If multiple voices are requested, they are averaged.
    Delimiter is optional and defaults to ','.
    """
    def load_voice(self, voice: Union[str, torch.FloatTensor], delimiter: str = ",") -> torch.FloatTensor:
        if isinstance(voice, torch.FloatTensor):
            return voice
        if voice in self.voices:
            return self.voices[voice]
        logger.debug(f"Loading voice: {voice}")
        packs = [self.load_single_voice(v) for v in voice.split(delimiter)]
        if len(packs) == 1:
            return packs[0]
        self.voices[voice] = torch.mean(torch.stack(packs), dim=0)
        return self.voices[voice]

    @staticmethod
    def tokens_to_ps(tokens: List[en.MToken]) -> str:
        return ''.join(t.phonemes + (' ' if t.whitespace else '') for t in tokens).strip()

    @staticmethod
    def waterfall_last(
        tokens: List[en.MToken],
        next_count: int,
        max_phonemes: int = MODEL_PHONEME_LIMIT,
        waterfall: List[str] = ['!.?…', ':;', ',—'],
        bumps: List[str] = [')', '”']
    ) -> int:
        for w in waterfall:
            z = next((i for i, t in reversed(list(enumerate(tokens))) if t.phonemes in set(w)), None)
            if z is None:
                continue
            z += 1
            if z < len(tokens) and tokens[z].phonemes in bumps:
                z += 1
            if next_count - len(KPipeline.tokens_to_ps(tokens[:z])) <= max_phonemes:
                return z
        return len(tokens)

    @staticmethod
    def tokens_to_text(tokens: List[en.MToken]) -> str:
        return ''.join(t.text + t.whitespace for t in tokens).strip()

    def en_tokenize(
        self,
        tokens: List[en.MToken]
    ) -> Generator[Tuple[str, str, List[en.MToken]], None, None]:
        tks = []
        pcount = 0
        for t in tokens:
            # American English: ɾ => T
            t.phonemes = '' if t.phonemes is None else t.phonemes#.replace('ɾ', 'T')
            next_ps = t.phonemes + (' ' if t.whitespace else '')
            next_pcount = pcount + len(next_ps.rstrip())
            if next_pcount > ENGLISH_QUALITY_PHONEME_LIMIT:
                z = KPipeline.waterfall_last(
                    tks,
                    next_pcount,
                    max_phonemes=ENGLISH_QUALITY_PHONEME_LIMIT,
                )
                text = KPipeline.tokens_to_text(tks[:z])
                logger.debug(f"Chunking text at {z}: '{text[:30]}{'...' if len(text) > 30 else ''}'")
                ps = KPipeline.tokens_to_ps(tks[:z])
                yield text, ps, tks[:z]
                tks = tks[z:]
                pcount = len(KPipeline.tokens_to_ps(tks))
                if not tks:
                    next_ps = next_ps.lstrip()
            tks.append(t)
            pcount += len(next_ps)
        if tks:
            text = KPipeline.tokens_to_text(tks)
            ps = KPipeline.tokens_to_ps(tks)
            yield ''.join(text).strip(), ''.join(ps).strip(), tks

    @staticmethod
    def infer(
        model: KModel,
        ps: str,
        pack: torch.FloatTensor,
        speed: Union[float, Callable[[int], float]] = 1
    ) -> KModel.Output:
        if callable(speed):
            speed = speed(len(ps))
        return model(ps, pack[len(ps)-1], speed, return_output=True)

    def generate_from_tokens(
        self,
        tokens: Union[str, List[en.MToken]],
        voice: str,
        speed: float = 1,
        model: Optional[KModel] = None
    ) -> Generator['KPipeline.Result', None, None]:
        """Generate audio from either raw phonemes or pre-processed tokens.
        
        Args:
            tokens: Either a phoneme string or list of pre-processed MTokens
            voice: The voice to use for synthesis
            speed: Speech speed modifier (default: 1)
            model: Optional KModel instance (uses pipeline's model if not provided)
        
        Yields:
            KPipeline.Result containing the input tokens and generated audio
            
        Raises:
            ValueError: If no voice is provided or token sequence exceeds model limits
        """
        model = model or self.model
        if model and voice is None:
            raise ValueError('Specify a voice: pipeline.generate_from_tokens(..., voice="af_heart")')
        
        pack = self.load_voice(voice).to(model.device) if model else None

        # Handle raw phoneme string
        if isinstance(tokens, str):
            logger.debug("Processing phonemes from raw string")
            if len(tokens) > MODEL_PHONEME_LIMIT:
                raise ValueError(
                    f'Phoneme string too long: {len(tokens)} > {MODEL_PHONEME_LIMIT}'
                )
            output = KPipeline.infer(model, tokens, pack, speed) if model else None
            yield self.Result(graphemes='', phonemes=tokens, output=output)
            return
        
        logger.debug("Processing MTokens")
        # Handle pre-processed tokens
        for gs, ps, tks in self.en_tokenize(tokens):
            if not ps:
                continue
            elif len(ps) > MODEL_PHONEME_LIMIT:
                logger.warning(
                    f"Unexpected len(ps) == {len(ps)} > {MODEL_PHONEME_LIMIT} and ps == '{ps}'"
                )
                logger.warning(f"Truncating to {MODEL_PHONEME_LIMIT} characters")
                ps = ps[:MODEL_PHONEME_LIMIT]
            output = KPipeline.infer(model, ps, pack, speed) if model else None
            if output is not None and output.pred_dur is not None:
                KPipeline.join_timestamps(tks, output.pred_dur)
            yield self.Result(graphemes=gs, phonemes=ps, tokens=tks, output=output)

    @staticmethod
    def join_timestamps(tokens: List[en.MToken], pred_dur: torch.LongTensor):
        # Multiply by 600 to go from pred_dur frames to sample_rate 24000
        # Equivalent to dividing pred_dur frames by 40 to get timestamp in seconds
        # We will count nice round half-frames, so the divisor is 80
        MAGIC_DIVISOR = 80
        if not tokens or len(pred_dur) < 3:
            # We expect at least 3: <bos>, token, <eos>
            return
        # We track 2 counts, measured in half-frames: (left, right)
        # This way we can cut space characters in half
        # TODO: Is -3 an appropriate offset?
        left = right = 2 * max(0, pred_dur[0].item() - 3)
        # Updates:
        # left = right + (2 * token_dur) + space_dur
        # right = left + space_dur
        i = 1
        for t in tokens:
            if i >= len(pred_dur)-1:
                break
            if not t.phonemes:
                if t.whitespace:
                    i += 1
                    left = right + pred_dur[i].item()
                    right = left + pred_dur[i].item()
                    i += 1
                continue
            j = i + len(t.phonemes)
            if j >= len(pred_dur):
                break
            t.start_ts = left / MAGIC_DIVISOR
            token_dur = pred_dur[i: j].sum().item()
            space_dur = pred_dur[j].item() if t.whitespace else 0
            left = right + (2 * token_dur) + space_dur
            t.end_ts = left / MAGIC_DIVISOR
            right = left + space_dur
            i = j + (1 if t.whitespace else 0)

    @dataclass
    class Result:
        graphemes: str
        phonemes: str
        tokens: Optional[List[en.MToken]] = None
        output: Optional[KModel.Output] = None
        text_index: Optional[int] = None

        @property
        def audio(self) -> Optional[torch.FloatTensor]:
            return None if self.output is None else self.output.audio

        @property
        def pred_dur(self) -> Optional[torch.LongTensor]:
            return None if self.output is None else self.output.pred_dur

        ### MARK: BEGIN BACKWARD COMPAT ###
        def __iter__(self):
            yield self.graphemes
            yield self.phonemes
            yield self.audio

        def __getitem__(self, index):
            return [self.graphemes, self.phonemes, self.audio][index]

        def __len__(self):
            return 3
        #### MARK: END BACKWARD COMPAT ####

    def __call__(
        self,
        text: Union[str, List[str]],
        voice: Optional[str] = None,
        speed: Union[float, Callable[[int], float]] = 1,
        split_pattern: Optional[str] = r'\n+',
        model: Optional[KModel] = None,
        normalize_markdown_emphasis: bool = True,
    ) -> Generator['KPipeline.Result', None, None]:
        model = model or self.model
        if model and voice is None:
            raise ValueError('Specify a voice: en_us_pipeline(text="Hello world!", voice="af_heart")')
        pack = self.load_voice(voice).to(model.device) if model else None
        
        # Convert input to list of segments
        if isinstance(text, str):
            text = re.split(split_pattern, text.strip()) if split_pattern else [text]
            
        # Process each segment
        for graphemes_index, graphemes in enumerate(text):
            if not graphemes.strip():  # Skip empty segments
                continue
                
            # English processing
            if self.lang_code in 'ab':
                logger.debug(f"Processing English text: {graphemes[:50]}{'...' if len(graphemes) > 50 else ''}")
                spoken_graphemes = normalize_english_text(
                    graphemes,
                    normalize_markdown_emphasis=normalize_markdown_emphasis,
                )
                _, tokens = self.g2p(spoken_graphemes)
                correct_english_pronunciations(
                    tokens, british=self.lang_code == 'b'
                )
                for gs, ps, tks in self.en_tokenize(tokens):
                    if not ps:
                        continue
                    elif len(ps) > MODEL_PHONEME_LIMIT:
                        logger.warning(
                            f"Unexpected len(ps) == {len(ps)} > {MODEL_PHONEME_LIMIT} and ps == '{ps}'"
                        )
                        ps = ps[:MODEL_PHONEME_LIMIT]
                    output = KPipeline.infer(model, ps, pack, speed) if model else None
                    if output is not None and output.pred_dur is not None:
                        KPipeline.join_timestamps(tks, output.pred_dur)
                    yield self.Result(graphemes=gs, phonemes=ps, tokens=tks, output=output, text_index=graphemes_index)
            
            # Non-English processing with chunking
            else:
                for chunk, ps in self._phonemize_non_english(graphemes):
                    output = KPipeline.infer(model, ps, pack, speed) if model else None
                    yield self.Result(graphemes=chunk, phonemes=ps, output=output, text_index=graphemes_index)

    @staticmethod
    def _split_graphemes(text: str, max_characters: int = 400) -> List[str]:
        """Split on multilingual sentence boundaries, then enforce a hard size cap."""
        sentence_end = r"(?:(?<!\d)\.|\.(?!\d)|[!?。！？；;])+\s*"
        sentences = re.findall(rf".*?(?:{sentence_end}|$)", text, flags=re.DOTALL)
        chunks: List[str] = []
        current = ""

        for sentence in (part for part in sentences if part):
            if len(current) + len(sentence) <= max_characters:
                current += sentence
                continue
            if current:
                chunks.append(current)
                current = ""
            while len(sentence) > max_characters:
                split_at = KPipeline._preferred_split(sentence, max_characters)
                chunks.append(sentence[:split_at])
                sentence = sentence[split_at:]
            current = sentence

        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _preferred_split(text: str, limit: int) -> int:
        window = text[:limit]
        candidates = [window.rfind(character) for character in " \t\n,:，、"]
        split_at = max(candidates, default=-1)
        return split_at + 1 if split_at >= limit // 2 else limit

    def _phonemize_non_english(self, text: str) -> Generator[Tuple[str, str], None, None]:
        """Yield complete text as model-safe phoneme chunks without truncation."""
        pending = self._split_graphemes(text)
        while pending:
            chunk = pending.pop(0)
            if not chunk.strip():
                continue
            ps, _ = self.g2p(chunk)
            if not ps:
                continue
            if len(ps) <= MODEL_PHONEME_LIMIT:
                yield chunk, ps
                continue

            if len(chunk) <= 1:
                logger.warning(
                    f"Unable to split single grapheme with {len(ps)} phonemes; "
                    f"truncating to {MODEL_PHONEME_LIMIT}"
                )
                yield chunk, ps[:MODEL_PHONEME_LIMIT]
                continue

            split_at = self._preferred_split(chunk, max(1, len(chunk) // 2))
            pending[0:0] = [chunk[:split_at], chunk[split_at:]]
