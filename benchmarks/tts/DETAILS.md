# KokoroTTS Benchmark Details

Each official run appends per-language and per-voice aggregates here. Warmup requests are excluded.

## 03.10.2026 00:27:33 - 0.4-snapshot
Model: `hexgrad/Kokoro-82M`  
GPU: `NVIDIA GeForce RTX 5070 Ti (16303 MiB)`  
Device: `auto`  
Repetitions per voice: `5`  
Comment: Python 3.13 v0.4 all-voice baseline

### By Language

| Language | Voices | Requests | Audio | Total | Mean | P95 | RTF | Realtime speed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | 20 | 100 | 2097.000s | 120.438s | 1.204s | 1.519s | 0.0574 | 17.41x |
| British English | 8 | 40 | 822.750s | 51.666s | 1.292s | 1.944s | 0.0628 | 15.92x |
| Japanese | 5 | 25 | 712.125s | 48.269s | 1.931s | 2.424s | 0.0678 | 14.75x |
| Mandarin Chinese | 8 | 40 | 798.500s | 53.622s | 1.341s | 1.733s | 0.0672 | 14.89x |
| Spanish | 3 | 15 | 310.250s | 19.000s | 1.267s | 1.316s | 0.0612 | 16.33x |
| French | 1 | 5 | 105.500s | 7.561s | 1.512s | 1.651s | 0.0717 | 13.95x |
| Hindi | 4 | 20 | 446.625s | 29.457s | 1.473s | 1.796s | 0.0660 | 15.16x |
| Italian | 2 | 10 | 204.375s | 14.667s | 1.467s | 1.788s | 0.0718 | 13.93x |
| Brazilian Portuguese | 3 | 15 | 295.875s | 18.467s | 1.231s | 1.321s | 0.0624 | 16.02x |

### By Voice

| Language | Voice | Name | Requests | Audio | Mean | P95 | RTF | Realtime speed |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | `af_heart` | Heart | 5 | 112.125s | 1.354s | 1.411s | 0.0604 | 16.56x |
| American English | `af_bella` | Bella | 5 | 114.750s | 1.398s | 1.468s | 0.0609 | 16.41x |
| American English | `af_nicole` | Nicole | 5 | 168.625s | 1.539s | 1.648s | 0.0456 | 21.91x |
| American English | `af_aoede` | Aoede | 5 | 107.000s | 1.302s | 1.402s | 0.0608 | 16.43x |
| American English | `af_kore` | Kore | 5 | 103.250s | 1.425s | 1.465s | 0.0690 | 14.49x |
| American English | `af_sarah` | Sarah | 5 | 109.750s | 1.189s | 1.219s | 0.0542 | 18.46x |
| American English | `af_nova` | Nova | 5 | 94.250s | 0.787s | 0.827s | 0.0418 | 23.94x |
| American English | `af_sky` | Sky | 5 | 102.750s | 1.134s | 1.260s | 0.0552 | 18.13x |
| American English | `af_alloy` | Alloy | 5 | 94.000s | 0.998s | 1.017s | 0.0531 | 18.84x |
| American English | `af_jessica` | Jessica | 5 | 93.625s | 1.097s | 1.180s | 0.0586 | 17.07x |
| American English | `af_river` | River | 5 | 92.375s | 0.994s | 1.080s | 0.0538 | 18.58x |
| American English | `am_michael` | Michael | 5 | 121.375s | 1.172s | 1.270s | 0.0483 | 20.72x |
| American English | `am_fenrir` | Fenrir | 5 | 101.500s | 1.182s | 1.243s | 0.0582 | 17.18x |
| American English | `am_puck` | Puck | 5 | 98.750s | 1.221s | 1.284s | 0.0618 | 16.17x |
| American English | `am_echo` | Echo | 5 | 95.750s | 1.048s | 1.083s | 0.0547 | 18.28x |
| American English | `am_eric` | Eric | 5 | 89.875s | 1.570s | 1.643s | 0.0873 | 11.45x |
| American English | `am_liam` | Liam | 5 | 95.000s | 1.232s | 1.274s | 0.0648 | 15.42x |
| American English | `am_onyx` | Onyx | 5 | 94.000s | 1.095s | 1.142s | 0.0582 | 17.17x |
| American English | `am_santa` | Santa | 5 | 104.750s | 1.206s | 1.294s | 0.0576 | 17.37x |
| American English | `am_adam` | Adam | 5 | 103.500s | 1.144s | 1.189s | 0.0552 | 18.10x |
| British English | `bf_emma` | Emma | 5 | 101.250s | 1.202s | 1.309s | 0.0593 | 16.85x |
| British English | `bf_isabella` | Isabella | 5 | 102.250s | 1.418s | 1.474s | 0.0693 | 14.42x |
| British English | `bf_alice` | Alice | 5 | 101.875s | 1.351s | 1.514s | 0.0663 | 15.08x |
| British English | `bf_lily` | Lily | 5 | 101.125s | 1.291s | 1.351s | 0.0638 | 15.67x |
| British English | `bm_george` | George | 5 | 113.375s | 1.939s | 2.021s | 0.0855 | 11.69x |
| British English | `bm_fable` | Fable | 5 | 94.000s | 0.942s | 1.013s | 0.0501 | 19.95x |
| British English | `bm_lewis` | Lewis | 5 | 114.625s | 1.002s | 1.038s | 0.0437 | 22.88x |
| British English | `bm_daniel` | Daniel | 5 | 94.250s | 1.189s | 1.224s | 0.0631 | 15.86x |
| Japanese | `jf_alpha` | Alpha | 5 | 123.000s | 1.654s | 1.718s | 0.0673 | 14.87x |
| Japanese | `jf_gongitsune` | Gongitsune | 5 | 152.750s | 2.050s | 2.097s | 0.0671 | 14.90x |
| Japanese | `jf_nezumi` | Nezumi | 5 | 154.750s | 2.248s | 2.494s | 0.0726 | 13.77x |
| Japanese | `jf_tebukuro` | Tebukuro | 5 | 151.750s | 2.210s | 2.424s | 0.0728 | 13.73x |
| Japanese | `jm_kumo` | Kumo | 5 | 129.875s | 1.491s | 1.664s | 0.0574 | 17.42x |
| Mandarin Chinese | `zf_xiaobei` | Xiaobei | 5 | 117.000s | 1.580s | 1.667s | 0.0675 | 14.81x |
| Mandarin Chinese | `zf_xiaoni` | Xiaoni | 5 | 103.625s | 1.731s | 1.859s | 0.0835 | 11.97x |
| Mandarin Chinese | `zf_xiaoxiao` | Xiaoxiao | 5 | 99.625s | 1.508s | 1.595s | 0.0757 | 13.21x |
| Mandarin Chinese | `zf_xiaoyi` | Xiaoyi | 5 | 99.000s | 1.597s | 1.646s | 0.0806 | 12.40x |
| Mandarin Chinese | `zm_yunjian` | Yunjian | 5 | 95.250s | 1.144s | 1.229s | 0.0601 | 16.65x |
| Mandarin Chinese | `zm_yunxi` | Yunxi | 5 | 90.125s | 0.953s | 1.067s | 0.0529 | 18.91x |
| Mandarin Chinese | `zm_yunxia` | Yunxia | 5 | 105.500s | 1.395s | 1.478s | 0.0661 | 15.13x |
| Mandarin Chinese | `zm_yunyang` | Yunyang | 5 | 88.375s | 0.815s | 0.875s | 0.0461 | 21.68x |
| Spanish | `ef_dora` | Dora | 5 | 103.500s | 1.266s | 1.315s | 0.0612 | 16.35x |
| Spanish | `em_alex` | Alex | 5 | 103.625s | 1.291s | 1.314s | 0.0623 | 16.05x |
| Spanish | `em_santa` | Santa | 5 | 103.125s | 1.243s | 1.279s | 0.0603 | 16.60x |
| French | `ff_siwis` | Siwis | 5 | 105.500s | 1.512s | 1.651s | 0.0717 | 13.95x |
| Hindi | `hf_alpha` | Alpha | 5 | 115.000s | 1.788s | 1.858s | 0.0777 | 12.86x |
| Hindi | `hf_beta` | Beta | 5 | 97.750s | 1.170s | 1.209s | 0.0599 | 16.71x |
| Hindi | `hm_omega` | Omega | 5 | 115.875s | 1.505s | 1.582s | 0.0649 | 15.40x |
| Hindi | `hm_psi` | Psi | 5 | 118.000s | 1.428s | 1.519s | 0.0605 | 16.52x |
| Italian | `if_sara` | Sara | 5 | 97.500s | 1.232s | 1.273s | 0.0632 | 15.83x |
| Italian | `im_nicola` | Nicola | 5 | 106.875s | 1.701s | 1.791s | 0.0796 | 12.56x |
| Brazilian Portuguese | `pf_dora` | Dora | 5 | 98.250s | 1.242s | 1.305s | 0.0632 | 15.82x |
| Brazilian Portuguese | `pm_alex` | Alex | 5 | 98.750s | 1.225s | 1.273s | 0.0620 | 16.13x |
| Brazilian Portuguese | `pm_santa` | Santa | 5 | 98.875s | 1.226s | 1.320s | 0.0620 | 16.12x |

## 03.10.2026 00:41:38 - 0.4-snapshot
Model: `hexgrad/Kokoro-82M`  
GPU: `NVIDIA GeForce RTX 5070 Ti (16303 MiB)`  
Device: `auto`  
Repetitions per voice: `5`  
Comment: None

### By Language

| Language | Voices | Requests | Audio | Total | Mean | P95 | RTF | Realtime speed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | 20 | 100 | 2097.000s | 118.252s | 1.183s | 1.535s | 0.0564 | 17.73x |
| British English | 8 | 40 | 822.750s | 50.790s | 1.270s | 1.879s | 0.0617 | 16.20x |
| Japanese | 5 | 25 | 712.125s | 47.658s | 1.906s | 2.236s | 0.0669 | 14.94x |
| Mandarin Chinese | 8 | 40 | 798.500s | 53.687s | 1.342s | 1.743s | 0.0672 | 14.87x |
| Spanish | 3 | 15 | 310.250s | 20.103s | 1.340s | 1.634s | 0.0648 | 15.43x |
| French | 1 | 5 | 105.500s | 7.890s | 1.578s | 1.949s | 0.0748 | 13.37x |
| Hindi | 4 | 20 | 446.625s | 32.757s | 1.638s | 2.147s | 0.0733 | 13.63x |
| Italian | 2 | 10 | 204.375s | 15.263s | 1.526s | 1.924s | 0.0747 | 13.39x |
| Brazilian Portuguese | 3 | 15 | 295.875s | 19.295s | 1.286s | 1.487s | 0.0652 | 15.33x |

### By Voice

| Language | Voice | Name | Requests | Audio | Mean | P95 | RTF | Realtime speed |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | `af_heart` | Heart | 5 | 112.125s | 1.351s | 1.503s | 0.0603 | 16.60x |
| American English | `af_bella` | Bella | 5 | 114.750s | 1.402s | 1.544s | 0.0611 | 16.37x |
| American English | `af_nicole` | Nicole | 5 | 168.625s | 1.619s | 1.825s | 0.0480 | 20.83x |
| American English | `af_aoede` | Aoede | 5 | 107.000s | 1.266s | 1.304s | 0.0592 | 16.91x |
| American English | `af_kore` | Kore | 5 | 103.250s | 1.390s | 1.455s | 0.0673 | 14.86x |
| American English | `af_sarah` | Sarah | 5 | 109.750s | 1.131s | 1.161s | 0.0515 | 19.40x |
| American English | `af_nova` | Nova | 5 | 94.250s | 0.748s | 0.774s | 0.0397 | 25.22x |
| American English | `af_sky` | Sky | 5 | 102.750s | 1.058s | 1.110s | 0.0515 | 19.42x |
| American English | `af_alloy` | Alloy | 5 | 94.000s | 1.004s | 1.069s | 0.0534 | 18.73x |
| American English | `af_jessica` | Jessica | 5 | 93.625s | 1.102s | 1.171s | 0.0589 | 16.99x |
| American English | `af_river` | River | 5 | 92.375s | 1.008s | 1.142s | 0.0546 | 18.32x |
| American English | `am_michael` | Michael | 5 | 121.375s | 1.148s | 1.242s | 0.0473 | 21.14x |
| American English | `am_fenrir` | Fenrir | 5 | 101.500s | 1.125s | 1.164s | 0.0554 | 18.05x |
| American English | `am_puck` | Puck | 5 | 98.750s | 1.183s | 1.229s | 0.0599 | 16.69x |
| American English | `am_echo` | Echo | 5 | 95.750s | 1.024s | 1.044s | 0.0535 | 18.70x |
| American English | `am_eric` | Eric | 5 | 89.875s | 1.501s | 1.556s | 0.0835 | 11.98x |
| American English | `am_liam` | Liam | 5 | 95.000s | 1.218s | 1.329s | 0.0641 | 15.60x |
| American English | `am_onyx` | Onyx | 5 | 94.000s | 1.095s | 1.209s | 0.0583 | 17.17x |
| American English | `am_santa` | Santa | 5 | 104.750s | 1.199s | 1.254s | 0.0572 | 17.47x |
| American English | `am_adam` | Adam | 5 | 103.500s | 1.077s | 1.112s | 0.0520 | 19.22x |
| British English | `bf_emma` | Emma | 5 | 101.250s | 1.151s | 1.166s | 0.0568 | 17.60x |
| British English | `bf_isabella` | Isabella | 5 | 102.250s | 1.397s | 1.462s | 0.0683 | 14.64x |
| British English | `bf_alice` | Alice | 5 | 101.875s | 1.311s | 1.341s | 0.0644 | 15.54x |
| British English | `bf_lily` | Lily | 5 | 101.125s | 1.223s | 1.310s | 0.0605 | 16.54x |
| British English | `bm_george` | George | 5 | 113.375s | 1.890s | 1.947s | 0.0834 | 12.00x |
| British English | `bm_fable` | Fable | 5 | 94.000s | 0.954s | 1.021s | 0.0507 | 19.71x |
| British English | `bm_lewis` | Lewis | 5 | 114.625s | 1.014s | 1.089s | 0.0442 | 22.61x |
| British English | `bm_daniel` | Daniel | 5 | 94.250s | 1.218s | 1.349s | 0.0646 | 15.48x |
| Japanese | `jf_alpha` | Alpha | 5 | 123.000s | 1.694s | 1.792s | 0.0689 | 14.52x |
| Japanese | `jf_gongitsune` | Gongitsune | 5 | 152.750s | 2.100s | 2.227s | 0.0687 | 14.55x |
| Japanese | `jf_nezumi` | Nezumi | 5 | 154.750s | 2.183s | 2.316s | 0.0705 | 14.18x |
| Japanese | `jf_tebukuro` | Tebukuro | 5 | 151.750s | 2.125s | 2.183s | 0.0700 | 14.28x |
| Japanese | `jm_kumo` | Kumo | 5 | 129.875s | 1.430s | 1.469s | 0.0551 | 18.16x |
| Mandarin Chinese | `zf_xiaobei` | Xiaobei | 5 | 117.000s | 1.584s | 1.724s | 0.0677 | 14.78x |
| Mandarin Chinese | `zf_xiaoni` | Xiaoni | 5 | 103.625s | 1.696s | 1.781s | 0.0818 | 12.22x |
| Mandarin Chinese | `zf_xiaoxiao` | Xiaoxiao | 5 | 99.625s | 1.517s | 1.627s | 0.0761 | 13.14x |
| Mandarin Chinese | `zf_xiaoyi` | Xiaoyi | 5 | 99.000s | 1.564s | 1.718s | 0.0790 | 12.66x |
| Mandarin Chinese | `zm_yunjian` | Yunjian | 5 | 95.250s | 1.164s | 1.335s | 0.0611 | 16.36x |
| Mandarin Chinese | `zm_yunxi` | Yunxi | 5 | 90.125s | 0.957s | 1.118s | 0.0531 | 18.83x |
| Mandarin Chinese | `zm_yunxia` | Yunxia | 5 | 105.500s | 1.398s | 1.612s | 0.0662 | 15.10x |
| Mandarin Chinese | `zm_yunyang` | Yunyang | 5 | 88.375s | 0.858s | 1.086s | 0.0486 | 20.59x |
| Spanish | `ef_dora` | Dora | 5 | 103.500s | 1.373s | 1.574s | 0.0663 | 15.08x |
| Spanish | `em_alex` | Alex | 5 | 103.625s | 1.371s | 1.605s | 0.0662 | 15.11x |
| Spanish | `em_santa` | Santa | 5 | 103.125s | 1.276s | 1.491s | 0.0619 | 16.16x |
| French | `ff_siwis` | Siwis | 5 | 105.500s | 1.578s | 1.949s | 0.0748 | 13.37x |
| Hindi | `hf_alpha` | Alpha | 5 | 115.000s | 1.919s | 2.361s | 0.0834 | 11.99x |
| Hindi | `hf_beta` | Beta | 5 | 97.750s | 1.313s | 1.522s | 0.0672 | 14.89x |
| Hindi | `hm_omega` | Omega | 5 | 115.875s | 1.764s | 2.096s | 0.0761 | 13.13x |
| Hindi | `hm_psi` | Psi | 5 | 118.000s | 1.555s | 1.850s | 0.0659 | 15.17x |
| Italian | `if_sara` | Sara | 5 | 97.500s | 1.291s | 1.422s | 0.0662 | 15.10x |
| Italian | `im_nicola` | Nicola | 5 | 106.875s | 1.762s | 2.001s | 0.0824 | 12.13x |
| Brazilian Portuguese | `pf_dora` | Dora | 5 | 98.250s | 1.294s | 1.430s | 0.0659 | 15.18x |
| Brazilian Portuguese | `pm_alex` | Alex | 5 | 98.750s | 1.308s | 1.514s | 0.0662 | 15.10x |
| Brazilian Portuguese | `pm_santa` | Santa | 5 | 98.875s | 1.257s | 1.355s | 0.0636 | 15.73x |

## 04.10.2026 05:04:25 - 1.0-snapshot
Model: `hexgrad/Kokoro-82M`  
GPU: `NVIDIA GeForce RTX 5070 Ti (16303 MiB)`  
Device: `auto`  
Repetitions per voice: `5`  
Comment: v1.0 post-upstream changes; shared GPU with idle Qwen container

### By Language

| Language | Voices | Requests | Audio | Total | Mean | P95 | RTF | Realtime speed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | 20 | 100 | 2097.000s | 121.571s | 1.216s | 1.561s | 0.0580 | 17.25x |
| British English | 8 | 40 | 822.750s | 50.302s | 1.258s | 1.891s | 0.0611 | 16.36x |
| Japanese | 5 | 25 | 909.250s | 61.889s | 2.476s | 2.895s | 0.0681 | 14.69x |
| Mandarin Chinese | 8 | 40 | 798.500s | 51.733s | 1.293s | 1.651s | 0.0648 | 15.44x |
| Spanish | 3 | 15 | 310.250s | 19.010s | 1.267s | 1.410s | 0.0613 | 16.32x |
| French | 1 | 5 | 105.500s | 7.400s | 1.480s | 1.544s | 0.0701 | 14.26x |
| Hindi | 4 | 20 | 446.625s | 30.078s | 1.504s | 1.944s | 0.0673 | 14.85x |
| Italian | 2 | 10 | 204.375s | 15.468s | 1.547s | 2.044s | 0.0757 | 13.21x |
| Brazilian Portuguese | 3 | 15 | 295.875s | 19.942s | 1.329s | 1.811s | 0.0674 | 14.84x |
| German | 2 | 10 | 246.625s | 15.655s | 1.565s | 2.181s | 0.0635 | 15.75x |
| Vietnamese | 14 | 70 | 1240.000s | 86.111s | 1.230s | 1.551s | 0.0694 | 14.40x |

### By Voice

| Language | Voice | Name | Requests | Audio | Mean | P95 | RTF | Realtime speed |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | `af_heart` | Heart | 5 | 112.125s | 1.382s | 1.520s | 0.0616 | 16.23x |
| American English | `af_bella` | Bella | 5 | 114.750s | 1.427s | 1.524s | 0.0622 | 16.08x |
| American English | `af_nicole` | Nicole | 5 | 168.625s | 1.504s | 1.655s | 0.0446 | 22.42x |
| American English | `af_aoede` | Aoede | 5 | 107.000s | 1.275s | 1.396s | 0.0596 | 16.78x |
| American English | `af_kore` | Kore | 5 | 103.250s | 1.465s | 1.621s | 0.0709 | 14.10x |
| American English | `af_sarah` | Sarah | 5 | 109.750s | 1.223s | 1.401s | 0.0557 | 17.94x |
| American English | `af_nova` | Nova | 5 | 94.250s | 0.815s | 0.917s | 0.0432 | 23.12x |
| American English | `af_sky` | Sky | 5 | 102.750s | 1.196s | 1.532s | 0.0582 | 17.19x |
| American English | `af_alloy` | Alloy | 5 | 94.000s | 1.193s | 1.469s | 0.0635 | 15.75x |
| American English | `af_jessica` | Jessica | 5 | 93.625s | 1.111s | 1.155s | 0.0594 | 16.85x |
| American English | `af_river` | River | 5 | 92.375s | 0.987s | 1.013s | 0.0534 | 18.71x |
| American English | `am_michael` | Michael | 5 | 121.375s | 1.178s | 1.330s | 0.0485 | 20.60x |
| American English | `am_fenrir` | Fenrir | 5 | 101.500s | 1.120s | 1.221s | 0.0552 | 18.12x |
| American English | `am_puck` | Puck | 5 | 98.750s | 1.203s | 1.340s | 0.0609 | 16.42x |
| American English | `am_echo` | Echo | 5 | 95.750s | 1.150s | 1.561s | 0.0601 | 16.65x |
| American English | `am_eric` | Eric | 5 | 89.875s | 1.529s | 1.640s | 0.0851 | 11.76x |
| American English | `am_liam` | Liam | 5 | 95.000s | 1.226s | 1.306s | 0.0645 | 15.50x |
| American English | `am_onyx` | Onyx | 5 | 94.000s | 1.071s | 1.098s | 0.0570 | 17.56x |
| American English | `am_santa` | Santa | 5 | 104.750s | 1.186s | 1.251s | 0.0566 | 17.66x |
| American English | `am_adam` | Adam | 5 | 103.500s | 1.071s | 1.095s | 0.0518 | 19.32x |
| British English | `bf_emma` | Emma | 5 | 101.250s | 1.106s | 1.132s | 0.0546 | 18.30x |
| British English | `bf_isabella` | Isabella | 5 | 102.250s | 1.409s | 1.511s | 0.0689 | 14.52x |
| British English | `bf_alice` | Alice | 5 | 101.875s | 1.367s | 1.465s | 0.0671 | 14.90x |
| British English | `bf_lily` | Lily | 5 | 101.125s | 1.210s | 1.300s | 0.0598 | 16.72x |
| British English | `bm_george` | George | 5 | 113.375s | 1.874s | 1.958s | 0.0827 | 12.10x |
| British English | `bm_fable` | Fable | 5 | 94.000s | 0.887s | 0.920s | 0.0472 | 21.20x |
| British English | `bm_lewis` | Lewis | 5 | 114.625s | 1.015s | 1.099s | 0.0443 | 22.58x |
| British English | `bm_daniel` | Daniel | 5 | 94.250s | 1.192s | 1.243s | 0.0632 | 15.81x |
| Japanese | `jf_alpha` | Alpha | 5 | 162.375s | 2.270s | 2.505s | 0.0699 | 14.30x |
| Japanese | `jf_gongitsune` | Gongitsune | 5 | 193.750s | 2.618s | 2.759s | 0.0676 | 14.80x |
| Japanese | `jf_nezumi` | Nezumi | 5 | 195.875s | 2.837s | 3.038s | 0.0724 | 13.81x |
| Japanese | `jf_tebukuro` | Tebukuro | 5 | 188.875s | 2.759s | 2.895s | 0.0730 | 13.69x |
| Japanese | `jm_kumo` | Kumo | 5 | 168.375s | 1.893s | 2.008s | 0.0562 | 17.79x |
| Mandarin Chinese | `zf_xiaobei` | Xiaobei | 5 | 117.000s | 1.475s | 1.501s | 0.0630 | 15.86x |
| Mandarin Chinese | `zf_xiaoni` | Xiaoni | 5 | 103.625s | 1.631s | 1.699s | 0.0787 | 12.71x |
| Mandarin Chinese | `zf_xiaoxiao` | Xiaoxiao | 5 | 99.625s | 1.471s | 1.552s | 0.0738 | 13.55x |
| Mandarin Chinese | `zf_xiaoyi` | Xiaoyi | 5 | 99.000s | 1.542s | 1.645s | 0.0779 | 12.84x |
| Mandarin Chinese | `zm_yunjian` | Yunjian | 5 | 95.250s | 1.068s | 1.118s | 0.0560 | 17.85x |
| Mandarin Chinese | `zm_yunxi` | Yunxi | 5 | 90.125s | 0.899s | 0.934s | 0.0499 | 20.05x |
| Mandarin Chinese | `zm_yunxia` | Yunxia | 5 | 105.500s | 1.416s | 1.584s | 0.0671 | 14.90x |
| Mandarin Chinese | `zm_yunyang` | Yunyang | 5 | 88.375s | 0.845s | 0.928s | 0.0478 | 20.91x |
| Spanish | `ef_dora` | Dora | 5 | 103.500s | 1.290s | 1.386s | 0.0623 | 16.05x |
| Spanish | `em_alex` | Alex | 5 | 103.625s | 1.279s | 1.399s | 0.0617 | 16.21x |
| Spanish | `em_santa` | Santa | 5 | 103.125s | 1.233s | 1.304s | 0.0598 | 16.72x |
| French | `ff_siwis` | Siwis | 5 | 105.500s | 1.480s | 1.544s | 0.0701 | 14.26x |
| Hindi | `hf_alpha` | Alpha | 5 | 115.000s | 1.743s | 1.952s | 0.0758 | 13.19x |
| Hindi | `hf_beta` | Beta | 5 | 97.750s | 1.182s | 1.307s | 0.0605 | 16.53x |
| Hindi | `hm_omega` | Omega | 5 | 115.875s | 1.591s | 1.871s | 0.0686 | 14.57x |
| Hindi | `hm_psi` | Psi | 5 | 118.000s | 1.499s | 1.790s | 0.0635 | 15.74x |
| Italian | `if_sara` | Sara | 5 | 97.500s | 1.288s | 1.598s | 0.0660 | 15.14x |
| Italian | `im_nicola` | Nicola | 5 | 106.875s | 1.806s | 2.194s | 0.0845 | 11.84x |
| Brazilian Portuguese | `pf_dora` | Dora | 5 | 98.250s | 1.351s | 1.629s | 0.0687 | 14.55x |
| Brazilian Portuguese | `pm_alex` | Alex | 5 | 98.750s | 1.307s | 1.670s | 0.0662 | 15.11x |
| Brazilian Portuguese | `pm_santa` | Santa | 5 | 98.875s | 1.330s | 1.764s | 0.0673 | 14.86x |
| German | `df_victoria` | Victoria | 5 | 134.250s | 1.466s | 1.845s | 0.0546 | 18.32x |
| German | `dm_martin` | Martin | 5 | 112.375s | 1.665s | 2.266s | 0.0741 | 13.50x |
| Vietnamese | `diem_trinh` | Diễm Trinh | 5 | 82.875s | 1.218s | 1.548s | 0.0735 | 13.61x |
| Vietnamese | `hung_thinh` | Hưng Thịnh | 5 | 82.125s | 1.080s | 1.339s | 0.0658 | 15.21x |
| Vietnamese | `mai_linh` | Mai Linh | 5 | 81.750s | 1.094s | 1.330s | 0.0669 | 14.94x |
| Vietnamese | `mai_loan` | Mai Loan | 5 | 100.000s | 1.352s | 1.582s | 0.0676 | 14.79x |
| Vietnamese | `manh_dung` | Mạnh Dũng | 5 | 87.625s | 1.139s | 1.341s | 0.0650 | 15.38x |
| Vietnamese | `my_yen` | Mỹ Yến | 5 | 95.000s | 1.274s | 1.498s | 0.0671 | 14.91x |
| Vietnamese | `ngoc_huyen` | Ngọc Huyền | 5 | 88.750s | 1.113s | 1.333s | 0.0627 | 15.95x |
| Vietnamese | `phat_tai` | Phát Tài | 5 | 88.500s | 1.317s | 1.505s | 0.0744 | 13.44x |
| Vietnamese | `thanh_dat` | Thành Đạt | 5 | 93.375s | 1.369s | 1.519s | 0.0733 | 13.64x |
| Vietnamese | `thuc_trinh` | Thục Trinh | 5 | 82.000s | 1.102s | 1.197s | 0.0672 | 14.88x |
| Vietnamese | `tuan_ngoc` | Tuấn Ngọc | 5 | 84.875s | 1.163s | 1.276s | 0.0685 | 14.60x |
| Vietnamese | `storyvert` | Storyvert | 5 | 106.875s | 1.451s | 1.567s | 0.0679 | 14.73x |
| Vietnamese | `duc_an` | Đức An | 5 | 86.250s | 1.260s | 1.386s | 0.0730 | 13.70x |
| Vietnamese | `duc_duy` | Đức Duy | 5 | 80.000s | 1.291s | 1.304s | 0.0807 | 12.40x |
