import random


SAMPLE_TEXTS = {
    "a": [
        "Choose a voice, adjust the speed if needed, then press Generate. Kokoro will turn this text into an MP3 before your coffee gets suspicious.",
        "A good demo sentence is like a good diner breakfast: simple, warm, and surprisingly effective.",
        "If this voice sounds relaxed, it is because the text has not seen the meeting agenda yet.",
        "The quick brown fox booked a podcast studio and asked the lazy dog to handle production.",
        "Press Generate, listen once, then pretend you knew the perfect voice all along.",
        "Every great audio test begins with a sentence that does not take itself too seriously.",
        "This is Kokoro TTS speaking clearly, calmly, and with no intention of joining a conference call.",
        "If the output sounds good, reward the model with another sentence and maybe fewer commas.",
        "A short text helps you test speed; a long paragraph helps you discover where the drama lives.",
        "Today feels like a good day to turn typed words into something that sounds almost too confident.",
    ],
    "b": [
        "Choose a voice, adjust the speed if needed, then press Generate. The tea may wait, but the MP3 will not.",
        "A proper test sentence should be clear, polite, and only mildly concerned about the weather.",
        "This voice is ready for narration, announcements, or explaining why the queue is moving slowly.",
        "The quick brown fox brought biscuits, and the lazy dog suddenly became much more cooperative.",
        "Press Generate and listen carefully; if it sounds posh, that is simply good manners.",
        "A small paragraph can reveal a lot, especially when it has punctuation and a tiny sense of occasion.",
        "Kokoro TTS is speaking from the web interface, probably with excellent posture.",
        "If this sounds natural, celebrate with a sensible volume level and a very calm nod.",
        "Try a short sentence first, then a longer one when the kettle has finished negotiating.",
        "The best audio tests are brief, cheerful, and unlikely to cause trouble at the village hall.",
    ],
    "j": [
        "音声を選び、速度を調整して、生成ボタンを押してください。お茶が冷める前に音声ができます。",
        "朝の駅のアナウンスみたいに、はっきり聞こえるか試してみましょう。",
        "短い文章から始めると、声の雰囲気がすぐにわかります。",
        "猫が会議に参加したら、たぶん一番落ち着いた声で話します。",
        "この文章は、日本語の読み上げが自然かどうかを確認するためのものです。",
        "雨の日のコンビニくらい、やさしくて便利な音声を目指します。",
        "生成ボタンを押したら、あとは音声ができるのを少し待つだけです。",
        "長い文章では、間の取り方や声の安定感を確認できます。",
        "たこ焼きが熱すぎる時のように、少しゆっくり話す設定も試せます。",
        "今日のテストは順調です。声も文章も、ほどよく元気です。",
    ],
    "z": [
        "请选择一个声音，调整语速，然后点击生成。咖啡还没凉，音频就准备好了。",
        "先试一句短话，就像点一碗面，先看看味道合不合适。",
        "这段文字用来测试中文发音、停顿和语气是否自然。",
        "如果熊猫也开播客，大概会先要求一个舒服的麦克风。",
        "点击生成后，请听一听声音是不是清楚、稳定、顺耳。",
        "长一点的段落可以帮助你检查节奏，就像听一段轻松的广播。",
        "今天的语音测试很顺利，连标点符号都显得很有礼貌。",
        "如果语速太快，可以慢一点；好声音不需要赶地铁。",
        "这句话没有复杂目的，只想让模型开开心心地读出来。",
        "试完短句以后，可以换成长文，看看声音能不能一直保持状态。",
    ],
    "e": [
        "Elige una voz, ajusta la velocidad y pulsa Generar. El MP3 saldrá antes de que se enfríe el café.",
        "Una buena frase de prueba debe sonar clara, natural y con un poco de sobremesa.",
        "Esta frase sirve para comprobar la pronunciación, el ritmo y la energía de la voz.",
        "Si un gato presentara un podcast, seguramente pediría una silla más cómoda.",
        "Prueba primero una frase corta; luego ya puedes sacar la novela de la abuela.",
        "Cuando la voz suena bien, hasta la lista de la compra parece importante.",
        "Hoy es un buen día para convertir texto en audio y fingir que fue fácil.",
        "Si la velocidad parece alta, bájala un poco; nadie quiere narrar como si perdiera el autobús.",
        "Esta prueba es ligera, amable y lista para sonar en español.",
        "Pulsa Generar, escucha el resultado y decide si la voz merece otra frase.",
    ],
    "f": [
        "Choisissez une voix, ajustez la vitesse, puis cliquez sur Générer. Le MP3 arrivera avant le café.",
        "Une bonne phrase de test doit être claire, naturelle, et juste assez élégante.",
        "Ce texte vérifie la prononciation, le rythme et la stabilité de la voix française.",
        "Si un chat animait une émission, il demanderait sûrement un coussin près du micro.",
        "Essayez d'abord une phrase courte, puis un paragraphe avec un peu plus de caractère.",
        "Quand la voix est bonne, même une recette de soupe semble prête pour la radio.",
        "Aujourd'hui, le texte devient audio sans faire de grand discours.",
        "Si le débit est trop rapide, ralentissez un peu; même le train attend parfois.",
        "Cette phrase est légère, utile, et prête à être lue à voix haute.",
        "Cliquez sur Générer, écoutez le résultat, puis choisissez la voix qui vous sourit le plus.",
    ],
    "h": [
        "एक आवाज़ चुनें, गति ठीक करें, फिर Generate दबाएँ। चाय ठंडी होने से पहले ऑडियो तैयार हो जाएगा।",
        "छोटे वाक्य से शुरुआत करें; जैसे पहले चाय की पहली चुस्की ली जाती है।",
        "यह वाक्य हिंदी उच्चारण, विराम और आवाज़ की स्थिरता जाँचने के लिए है।",
        "अगर बिल्ली पॉडकास्ट चलाती, तो शायद सबसे पहले आरामदायक कुर्सी माँगती।",
        "आवाज़ साफ़ लगे तो अगला वाक्य थोड़ा लंबा करके देखें।",
        "गति बहुत तेज़ लगे तो कम कर दें; अच्छी कहानी को भागने की ज़रूरत नहीं होती।",
        "आज का परीक्षण हल्का, साफ़ और सुनने में आसान होना चाहिए।",
        "यह टेक्स्ट सिर्फ़ इतना चाहता है कि आवाज़ स्वाभाविक और दोस्ताना लगे।",
        "लंबे पैराग्राफ से आप लय और ठहराव को बेहतर तरीके से परख सकते हैं।",
        "Generate दबाएँ, परिणाम सुनें, और तय करें कि यह आवाज़ आपकी कहानी के लिए सही है या नहीं।",
    ],
    "i": [
        "Scegli una voce, regola la velocità e premi Genera. L'MP3 arriverà prima del caffè.",
        "Una buona frase di prova deve essere chiara, naturale e un po' simpatica.",
        "Questo testo controlla pronuncia, ritmo e stabilità della voce italiana.",
        "Se un gatto avesse un podcast, chiederebbe prima un cuscino vicino al microfono.",
        "Prova una frase breve, poi passa a un paragrafo con più movimento.",
        "Quando la voce funziona, anche la lista della spesa sembra pronta per il teatro.",
        "Oggi il testo diventa audio senza fare troppe storie.",
        "Se la velocità corre troppo, rallentala; non siamo mica in stazione.",
        "Questa frase è leggera, utile e pronta per essere ascoltata.",
        "Premi Genera, ascolta il risultato e scegli la voce che ti convince di più.",
    ],
    "p": [
        "Escolha uma voz, ajuste a velocidade e clique em Gerar. O MP3 sai antes do café esfriar.",
        "Uma boa frase de teste precisa ser clara, natural e com um pouco de bom humor.",
        "Este texto ajuda a verificar pronúncia, ritmo e estabilidade em português do Brasil.",
        "Se um gato tivesse podcast, pediria primeiro uma cadeira confortável perto do microfone.",
        "Teste uma frase curta; depois mande um parágrafo com mais emoção.",
        "Quando a voz fica boa, até lista de mercado parece narração de documentário.",
        "Hoje é um ótimo dia para transformar texto em áudio sem complicar a vida.",
        "Se a velocidade estiver alta, diminua um pouco; boa história não precisa correr.",
        "Esta frase é leve, útil e pronta para soar de um jeito simpático.",
        "Clique em Gerar, escute o resultado e escolha a voz que combina melhor com seu texto.",
    ],
    "d": [
        "Wählen Sie eine Stimme, passen Sie bei Bedarf das Tempo an und klicken Sie auf Erzeugen. Kokoro macht daraus eine Audiodatei, bevor der Kaffee misstrauisch wird.",
        "Ein guter Testsatz klingt klar, natürlich und nimmt sich selbst nicht zu ernst.",
        "Dieser Text prüft die deutsche Aussprache, Pausen und den Rhythmus der Stimme.",
        "Wenn eine Katze einen Podcast hätte, würde sie zuerst einen bequemeren Stuhl verlangen.",
        "Beginnen Sie mit einem kurzen Satz und probieren Sie danach einen längeren Absatz.",
        "Wenn die Stimme gut klingt, wirkt sogar die Einkaufsliste wie eine wichtige Durchsage.",
        "Heute ist ein guter Tag, um geschriebenen Text ohne Umwege hörbar zu machen.",
        "Ist das Tempo zu hoch, stellen Sie es etwas langsamer; gute Geschichten müssen nicht rennen.",
        "Dieser Satz ist freundlich, nützlich und bereit für einen gründlichen Hörtest.",
        "Klicken Sie auf Erzeugen, hören Sie das Ergebnis an und wählen Sie Ihre Lieblingsstimme.",
    ],
}

def get_language_code_for_voice(voice="af_heart") -> str:
    if not voice:
        return "a"
    return voice[0] if voice[0] in SAMPLE_TEXTS else "a"


def get_intro_text(voice="af_heart"):
    language_code = get_language_code_for_voice(voice)
    return SAMPLE_TEXTS[language_code][0]


def get_random_quote(voice="af_heart"):
    language_code = get_language_code_for_voice(voice)
    return random.choice(SAMPLE_TEXTS[language_code])


def get_initial_text():
    return get_intro_text("af_heart")
