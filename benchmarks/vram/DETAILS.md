# KokoroTTS VRAM Benchmark Details

Each official run appends lifecycle, per-language, and per-voice GPU memory measurements here.

## 2026-10-03 03:20:48 UTC - 0.4-snapshot
- Model: `hexgrad/Kokoro-82M`
- GPU: `NVIDIA GeForce RTX 5070 Ti (16303 MiB)`
- Sample interval: `50 ms`
- Comment: Official quiet-GPU RTX 5070 Ti baseline for v0.4-snapshot; full catalog with lifecycle, per-language, and per-voice measurements

### Lifecycle Stages

| Stage | Process allocated | Process reserved | Process peak allocated | Process peak reserved | Device used |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before runtime | 0.0 MiB | 0.0 MiB | 0.0 MiB | 0.0 MiB | 1293.6 MiB |
| After voice preparation | 0.0 MiB | 0.0 MiB | 0.0 MiB | 0.0 MiB | 1293.6 MiB |
| After initial model weights | 317.6 MiB | 332.0 MiB | 317.6 MiB | 332.0 MiB | 1673.6 MiB |
| After all inference | 1283.5 MiB | 1324.0 MiB | 1725.1 MiB | 2052.0 MiB | 2687.6 MiB |

### By Language

| Language | Voices | Process peak allocated | Process peak reserved | Peak voice | Device peak | Device peak voice |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| American English | 20 | 1022.0 MiB | 1356.0 MiB | `af_nicole` | 2715.6 MiB | `af_nicole` |
| British English | 8 | 800.2 MiB | 1064.0 MiB | `bm_lewis` | 2425.6 MiB | `bm_lewis` |
| Japanese | 5 | 962.2 MiB | 1430.0 MiB | `jf_nezumi` | 2791.6 MiB | `jf_nezumi` |
| Mandarin Chinese | 8 | 809.6 MiB | 1082.0 MiB | `zf_xiaoni` | 2443.6 MiB | `zf_xiaoni` |
| Spanish | 3 | 756.9 MiB | 1096.0 MiB | `ef_dora` | 2457.6 MiB | `ef_dora` |
| French | 1 | 764.2 MiB | 982.0 MiB | `ff_siwis` | 2343.6 MiB | `ff_siwis` |
| Hindi | 4 | 817.3 MiB | 1208.0 MiB | `hm_omega` | 2569.6 MiB | `hm_omega` |
| Italian | 2 | 767.0 MiB | 1152.0 MiB | `im_nicola` | 2513.6 MiB | `im_nicola` |
| Brazilian Portuguese | 3 | 735.4 MiB | 1048.0 MiB | `pf_dora` | 2409.6 MiB | `pf_dora` |
| German | 2 | 1430.7 MiB | 1658.0 MiB | `dm_martin` | 3019.6 MiB | `dm_martin` |
| Vietnamese | 14 | 1725.1 MiB | 2052.0 MiB | `storyvert` | 3413.6 MiB | `storyvert` |

### By Voice

| Language | Voice | Name | Audio | Process peak allocated | Process peak reserved | Inference increment | Device baseline | Device peak | Samples |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| American English | `af_heart` | Heart | 22.425s | 789.4 MiB | 1124.0 MiB | 792.0 MiB | 1673.6 MiB | 2483.6 MiB | 42 |
| American English | `af_bella` | Bella | 22.950s | 799.6 MiB | 1064.0 MiB | 732.0 MiB | 1713.6 MiB | 2423.6 MiB | 6 |
| American English | `af_nicole` | Nicole | 33.725s | 1022.0 MiB | 1356.0 MiB | 1024.0 MiB | 1713.6 MiB | 2715.6 MiB | 7 |
| American English | `af_aoede` | Aoede | 21.400s | 769.0 MiB | 1134.0 MiB | 802.0 MiB | 1713.6 MiB | 2493.6 MiB | 7 |
| American English | `af_kore` | Kore | 20.650s | 753.1 MiB | 1076.0 MiB | 744.0 MiB | 1713.6 MiB | 2437.6 MiB | 7 |
| American English | `af_sarah` | Sarah | 21.950s | 781.1 MiB | 1024.0 MiB | 692.0 MiB | 1715.6 MiB | 2385.6 MiB | 6 |
| American English | `af_nova` | Nova | 18.850s | 716.6 MiB | 990.0 MiB | 658.0 MiB | 1715.6 MiB | 2351.6 MiB | 6 |
| American English | `af_sky` | Sky | 20.550s | 751.1 MiB | 1088.0 MiB | 756.0 MiB | 1715.6 MiB | 2449.6 MiB | 6 |
| American English | `af_alloy` | Alloy | 18.800s | 714.6 MiB | 990.0 MiB | 658.0 MiB | 1715.6 MiB | 2351.6 MiB | 6 |
| American English | `af_jessica` | Jessica | 18.725s | 714.0 MiB | 890.0 MiB | 558.0 MiB | 1715.6 MiB | 2251.6 MiB | 6 |
| American English | `af_river` | River | 18.475s | 710.6 MiB | 888.0 MiB | 556.0 MiB | 1715.6 MiB | 2249.6 MiB | 7 |
| American English | `am_michael` | Michael | 24.275s | 825.8 MiB | 1126.0 MiB | 794.0 MiB | 1715.6 MiB | 2487.6 MiB | 6 |
| American English | `am_fenrir` | Fenrir | 20.300s | 747.4 MiB | 960.0 MiB | 628.0 MiB | 1715.6 MiB | 2321.6 MiB | 6 |
| American English | `am_puck` | Puck | 19.750s | 735.8 MiB | 1048.0 MiB | 716.0 MiB | 1715.6 MiB | 2409.6 MiB | 6 |
| American English | `am_echo` | Echo | 19.150s | 721.9 MiB | 900.0 MiB | 568.0 MiB | 1715.6 MiB | 2261.6 MiB | 6 |
| American English | `am_eric` | Eric | 17.975s | 698.5 MiB | 950.0 MiB | 618.0 MiB | 1715.6 MiB | 2311.6 MiB | 5 |
| American English | `am_liam` | Liam | 19.000s | 720.8 MiB | 988.0 MiB | 656.0 MiB | 1715.6 MiB | 2349.6 MiB | 6 |
| American English | `am_onyx` | Onyx | 18.800s | 714.8 MiB | 990.0 MiB | 658.0 MiB | 1715.6 MiB | 2351.6 MiB | 5 |
| American English | `am_santa` | Santa | 20.950s | 762.1 MiB | 982.0 MiB | 650.0 MiB | 1715.6 MiB | 2343.6 MiB | 6 |
| American English | `am_adam` | Adam | 20.700s | 755.4 MiB | 1094.0 MiB | 762.0 MiB | 1715.6 MiB | 2455.6 MiB | 6 |
| British English | `bf_emma` | Emma | 20.250s | 746.3 MiB | 960.0 MiB | 628.0 MiB | 1715.6 MiB | 2321.6 MiB | 6 |
| British English | `bf_isabella` | Isabella | 20.450s | 748.7 MiB | 964.0 MiB | 632.0 MiB | 1715.6 MiB | 2325.6 MiB | 6 |
| British English | `bf_alice` | Alice | 20.375s | 748.7 MiB | 962.0 MiB | 630.0 MiB | 1715.6 MiB | 2323.6 MiB | 6 |
| British English | `bf_lily` | Lily | 20.225s | 746.6 MiB | 996.0 MiB | 664.0 MiB | 1715.6 MiB | 2357.6 MiB | 6 |
| British English | `bm_george` | George | 22.675s | 796.5 MiB | 1062.0 MiB | 730.0 MiB | 1715.6 MiB | 2423.6 MiB | 6 |
| British English | `bm_fable` | Fable | 18.800s | 715.1 MiB | 988.0 MiB | 656.0 MiB | 1715.6 MiB | 2349.6 MiB | 5 |
| British English | `bm_lewis` | Lewis | 22.925s | 800.2 MiB | 1064.0 MiB | 732.0 MiB | 1715.6 MiB | 2425.6 MiB | 6 |
| British English | `bm_daniel` | Daniel | 18.850s | 717.1 MiB | 988.0 MiB | 656.0 MiB | 1715.6 MiB | 2349.6 MiB | 5 |
| Japanese | `jf_alpha` | Alpha | 24.600s | 833.7 MiB | 1052.0 MiB | 720.0 MiB | 1715.6 MiB | 2413.6 MiB | 6 |
| Japanese | `jf_gongitsune` | Gongitsune | 30.550s | 956.7 MiB | 1318.0 MiB | 986.0 MiB | 1715.6 MiB | 2679.6 MiB | 6 |
| Japanese | `jf_nezumi` | Nezumi | 30.950s | 962.2 MiB | 1430.0 MiB | 1098.0 MiB | 1715.6 MiB | 2791.6 MiB | 6 |
| Japanese | `jf_tebukuro` | Tebukuro | 30.350s | 952.8 MiB | 1318.0 MiB | 986.0 MiB | 1715.6 MiB | 2679.6 MiB | 6 |
| Japanese | `jm_kumo` | Kumo | 25.975s | 859.3 MiB | 1150.0 MiB | 818.0 MiB | 1715.6 MiB | 2511.6 MiB | 6 |
| Mandarin Chinese | `zf_xiaobei` | Xiaobei | 23.400s | 809.6 MiB | 1068.0 MiB | 736.0 MiB | 1715.6 MiB | 2429.6 MiB | 15 |
| Mandarin Chinese | `zf_xiaoni` | Xiaoni | 20.725s | 756.8 MiB | 1082.0 MiB | 750.0 MiB | 1715.6 MiB | 2443.6 MiB | 6 |
| Mandarin Chinese | `zf_xiaoxiao` | Xiaoxiao | 19.925s | 739.1 MiB | 928.0 MiB | 596.0 MiB | 1715.6 MiB | 2289.6 MiB | 6 |
| Mandarin Chinese | `zf_xiaoyi` | Xiaoyi | 19.800s | 736.2 MiB | 1020.0 MiB | 688.0 MiB | 1715.6 MiB | 2381.6 MiB | 6 |
| Mandarin Chinese | `zm_yunjian` | Yunjian | 19.050s | 723.5 MiB | 964.0 MiB | 632.0 MiB | 1715.6 MiB | 2325.6 MiB | 6 |
| Mandarin Chinese | `zm_yunxi` | Yunxi | 18.025s | 700.8 MiB | 942.0 MiB | 610.0 MiB | 1715.6 MiB | 2303.6 MiB | 6 |
| Mandarin Chinese | `zm_yunxia` | Yunxia | 21.100s | 767.2 MiB | 988.0 MiB | 656.0 MiB | 1715.6 MiB | 2349.6 MiB | 6 |
| Mandarin Chinese | `zm_yunyang` | Yunyang | 17.675s | 695.8 MiB | 844.0 MiB | 512.0 MiB | 1715.6 MiB | 2205.6 MiB | 5 |
| Spanish | `ef_dora` | Dora | 20.700s | 756.9 MiB | 1096.0 MiB | 764.0 MiB | 1715.6 MiB | 2457.6 MiB | 5 |
| Spanish | `em_alex` | Alex | 20.725s | 756.4 MiB | 1076.0 MiB | 744.0 MiB | 1715.6 MiB | 2437.6 MiB | 6 |
| Spanish | `em_santa` | Santa | 20.625s | 752.9 MiB | 1090.0 MiB | 758.0 MiB | 1715.6 MiB | 2451.6 MiB | 5 |
| French | `ff_siwis` | Siwis | 21.100s | 764.2 MiB | 982.0 MiB | 650.0 MiB | 1715.6 MiB | 2343.6 MiB | 6 |
| Hindi | `hf_alpha` | Alpha | 23.000s | 801.8 MiB | 1090.0 MiB | 758.0 MiB | 1715.6 MiB | 2451.6 MiB | 6 |
| Hindi | `hf_beta` | Beta | 19.550s | 731.7 MiB | 916.0 MiB | 584.0 MiB | 1715.6 MiB | 2277.6 MiB | 6 |
| Hindi | `hm_omega` | Omega | 23.175s | 805.8 MiB | 1208.0 MiB | 876.0 MiB | 1715.6 MiB | 2569.6 MiB | 7 |
| Hindi | `hm_psi` | Psi | 23.600s | 817.3 MiB | 1070.0 MiB | 738.0 MiB | 1715.6 MiB | 2431.6 MiB | 6 |
| Italian | `if_sara` | Sara | 19.500s | 732.7 MiB | 944.0 MiB | 612.0 MiB | 1715.6 MiB | 2305.6 MiB | 6 |
| Italian | `im_nicola` | Nicola | 21.375s | 767.0 MiB | 1152.0 MiB | 820.0 MiB | 1715.6 MiB | 2513.6 MiB | 6 |
| Brazilian Portuguese | `pf_dora` | Dora | 19.650s | 733.1 MiB | 1048.0 MiB | 716.0 MiB | 1715.6 MiB | 2409.6 MiB | 6 |
| Brazilian Portuguese | `pm_alex` | Alex | 19.750s | 735.1 MiB | 1048.0 MiB | 716.0 MiB | 1715.6 MiB | 2409.6 MiB | 5 |
| Brazilian Portuguese | `pm_santa` | Santa | 19.775s | 735.4 MiB | 1048.0 MiB | 716.0 MiB | 1715.6 MiB | 2409.6 MiB | 5 |
| German | `df_victoria` | Victoria | 26.850s | 1198.1 MiB | 1532.0 MiB | 1200.0 MiB | 1715.6 MiB | 2893.6 MiB | 26 |
| German | `dm_martin` | Martin | 22.475s | 1430.7 MiB | 1658.0 MiB | 1326.0 MiB | 2045.6 MiB | 3019.6 MiB | 22 |
| Vietnamese | `diem_trinh` | Diễm Trinh | 16.575s | 1627.7 MiB | 1800.0 MiB | 1468.0 MiB | 2349.6 MiB | 3161.6 MiB | 24 |
| Vietnamese | `hung_thinh` | Hưng Thịnh | 16.425s | 1624.5 MiB | 1876.0 MiB | 1544.0 MiB | 2665.6 MiB | 3237.6 MiB | 7 |
| Vietnamese | `mai_linh` | Mai Linh | 16.350s | 1625.2 MiB | 1876.0 MiB | 1544.0 MiB | 2685.6 MiB | 3237.6 MiB | 7 |
| Vietnamese | `mai_loan` | Mai Loan | 20.000s | 1699.2 MiB | 1932.0 MiB | 1600.0 MiB | 2665.6 MiB | 3293.6 MiB | 7 |
| Vietnamese | `manh_dung` | Mạnh Dũng | 17.525s | 1649.0 MiB | 1826.0 MiB | 1494.0 MiB | 2685.6 MiB | 3187.6 MiB | 7 |
| Vietnamese | `my_yen` | Mỹ Yến | 19.000s | 1680.0 MiB | 1946.0 MiB | 1614.0 MiB | 2685.6 MiB | 3307.6 MiB | 7 |
| Vietnamese | `ngoc_huyen` | Ngọc Huyền | 17.750s | 1654.6 MiB | 1824.0 MiB | 1492.0 MiB | 2665.6 MiB | 3185.6 MiB | 7 |
| Vietnamese | `phat_tai` | Phát Tài | 17.700s | 1652.7 MiB | 1794.0 MiB | 1462.0 MiB | 2685.6 MiB | 3155.6 MiB | 7 |
| Vietnamese | `thanh_dat` | Thành Đạt | 18.675s | 1670.3 MiB | 1814.0 MiB | 1482.0 MiB | 2685.6 MiB | 3175.6 MiB | 7 |
| Vietnamese | `thuc_trinh` | Thục Trinh | 16.400s | 1624.2 MiB | 1848.0 MiB | 1516.0 MiB | 2665.6 MiB | 3209.6 MiB | 7 |
| Vietnamese | `tuan_ngoc` | Tuấn Ngọc | 16.975s | 1638.7 MiB | 1778.0 MiB | 1446.0 MiB | 2685.6 MiB | 3139.6 MiB | 7 |
| Vietnamese | `storyvert` | Storyvert | 21.375s | 1725.1 MiB | 2052.0 MiB | 1720.0 MiB | 2685.6 MiB | 3413.6 MiB | 6 |
| Vietnamese | `duc_an` | Đức An | 17.250s | 1642.2 MiB | 1872.0 MiB | 1540.0 MiB | 2665.6 MiB | 3235.6 MiB | 7 |
| Vietnamese | `duc_duy` | Đức Duy | 16.000s | 1618.1 MiB | 1758.0 MiB | 1426.0 MiB | 2687.6 MiB | 3121.6 MiB | 6 |
