# Data

What the data files are, which one to use, and how each was made. Read this before running any experiment.

## Where the data lives

Data is not in git. The same layout is used locally and on Google Drive:

```
datasets/                       local, in the repository folder (git-ignored)
<QOE_DRIVE_DIR>/datasets/       Google Drive: phd/research/major_revision/datasets
  cod/  freefire/  pubg/  gob/  all_games/
```

Game codes are always `cod`, `freefire`, `pubg`, `gob`. File names follow `<content>_<game>_<window>[_<variant>].csv`:

| File | Content |
|---|---|
| `features_<game>_<W>s.csv` | 62 features + `ping`, one row per labelled second, window W seconds, **standard** extractor |
| `features_<game>_<W>s_paper.csv` | the frozen dataset behind the paper's numbers |
| `features_<game>_<W>s_legacy.csv` | made by the original per-game extractor (`--mode legacy`) |
| `labels_<game>.csv` | one row per match: `folder`, `pcapng_file`, `time_value_pairs` (OCR ping per second) |
| `matches_<game>.csv` | per-match statistics (duration, packets); last row `average` is a summary |

The raw captures (`.pcap`/`.pcapng`) are in the Drive zips under `raw_pcaps/` and are extracted to `datasets/<game>/` (any sub-folder; the extractor finds each capture by run folder and file name).

## Which file to use

| Purpose | Use |
|---|---|
| Reproduce a number reported in the paper | `features_<game>_10s_paper.csv` |
| New experiments | `features/extract.py --mode standard`, i.e. `features_<game>_<W>s.csv` |
| Reproduce the paper's window-size figure (#47) | `features_cod_<W>s_legacy.csv` |

### Official files

| File | Rows | md5 |
|---|---|---|
| `cod/features_cod_10s_paper.csv` | 88,682 | `eb70da48e2dab8c82df48658e642cdf1` |
| `freefire/features_freefire_10s_paper.csv` | 107,189 | `43c1f4c62ea9e94d82046463886e0af9` |
| `pubg/features_pubg_10s_paper.csv` | 65,982 | `b8a89166c705b1e078de152a50a2d51c` |
| `gob/features_gob_10s_paper.csv` | 50,828 | `a59241ea3dd5277d3c322f3f124a907e` |
| `all_games/features_all_games_10s_paper.csv` | 447,233 | `9c7092ced094dc45e5b9ea40da4fa22a` |
| `all_games/features_all_games_10s_62features.csv` | 306,825 | `221aecfde6d044fb2557728ee73c2c9a` |
| `cod/features_cod_10s.csv` | 109,174 | `6771f5aab9aceb7f6cb2d321a2888477` |
| `freefire/features_freefire_10s.csv` | 133,172 | `04c1b55565d136176b925ef7a11c28c6` |
| `pubg/features_pubg_10s.csv` | 67,257 | `0d0f6646285a0340bee1d81c4b82476c` |
| `gob/features_gob_10s.csv` | 59,319 | `60187906bc6d46bbb303f912c97097ab` |
| `all_games/features_all_games_10s.csv` | 368,922 | `c13eaa7dd0d4545b0541ca02e53b7e21` |
| `cod/features_cod_1s_legacy.csv` | 90,355 | `abd28985f894deaa926b2ab902d23607` |
| `cod/features_cod_3s_legacy.csv` | 90,080 | `5cd6e5ec52c1395e43e795e2baf9bf51` |
| `cod/features_cod_5s_legacy.csv` | 89,691 | `cec1ff410032f081454260729fccdf5e` |
| `cod/features_cod_10s_legacy.csv` | 88,704 | `db1c0b79f77f9f345cb4cea652cbba29` |
| `cod/features_cod_15s_legacy.csv` | 87,799 | `dd5421cd7bef919cc1f853c8d518f2b3` |
| `cod/labels_cod.csv` | 616 matches | `da8ab99fe85daede6d9a2da5f9670c57` |
| `freefire/labels_freefire.csv` | 407 | `685e592c1b93b9af1b429674e3b10780` |
| `pubg/labels_pubg.csv` | 199 (184 used) | `96a377cde07c26e63c784150a466d38c` |
| `gob/labels_gob.csv` | 300 | `71fc6d6c5a9f16f52940a183eb190ffc` |

Check a file with `md5 <file>` (macOS) or `md5sum <file>`.

### Provenance of the paper datasets

| Paper file | Original name | Notes |
|---|---|---|
| `features_cod_10s_paper.csv` | `dataset_C_O_D_new_ficher.csv` | |
| `features_freefire_10s_paper.csv` | `dataset_FF_new_ficher.csv` | |
| `features_pubg_10s_paper.csv` | `combined_PUBG_new_ficher.csv` | = `dataset_PUBG_new_ficher.csv` + `window_10_1777833895.csv` (the 7 balancing runs of 2026-05-03, each included twice) |
| `features_gob_10s_paper.csv` | `dataset_Guns_Of_Boom_new_ficher.csv` | |
| `features_all_games_10s_paper.csv` | `combined_dataset_C_O_D__Guns_Of_Boom.csv____PUBG___michael.csv` (2026-04-01) | the pooled table was trained on the **30** conference features of this file |
| `features_all_games_10s_62features.csv` | `combined_4_games_dataset_new_ficher.csv` (2026-04-30) | the four 62-feature datasets concatenated (base PUBG file); not used in the paper |

## Pipeline

```bash
python features/extract.py --game cod [--window 10] [--mode standard|legacy]   # captures + labels -> features
python training/run_models.py --game cod [--window 10] [--tag paper] [--classes 3 5] [--features 62|30|47]
```

`run_models.py` is the paper's training code (`modelse.py`, logic unchanged): 5-fold StratifiedKFold (shuffle, seed 42), no SMOTE unless `--smote`. Results are written to `datasets/<game>/results/<dataset>_f<features>/class_<N>/<smote|no_smote>/`.

Environment that reproduces the paper: Python 3.13, scikit-learn 1.7.2 (`modelse.py` passes `LogisticRegression(multi_class=...)`, removed in 1.8), pandas 2.2.3, xgboost 3.4.1, nfstream 6.6.0.

### Reproducing the paper's tables

`run_models.py --tag paper` reproduces every per-game table in the paper within 0.001 (GoB XGBoost within 0.005), and the pooled table with `--game all_games --tag paper --features 30`:

| Run | RF accuracy / Macro F1 | Paper |
|---|---|---|
| `--game cod --tag paper` | 0.910 / 0.899 | 0.910 / 0.899 |
| `--game cod --tag paper --classes 5` | 0.849 / 0.843 | 0.848 / 0.842 |
| `--game freefire --tag paper` | 0.892 / 0.879 | 0.892 / 0.879 |
| `--game pubg --tag paper` | 0.896 / 0.884 | 0.895 / 0.884 |
| `--game gob --tag paper` | 0.735 / 0.724 | 0.736 / 0.724 |
| `--game all_games --tag paper --features 30` | 0.938 / 0.935 | 0.938 / 0.935 |

## The feature extractor

`features/extract.py` is one extractor for all games; `features/games.py` holds the per-game settings.

**Per game (traffic selection, as in the paper's methodology):** CoD keeps UDP ports 7000 to 10000, Free Fire ports 10010 to 10025, PUBG game ports plus server IP prefixes (`pubg/out/tencent.csv`), GoB all UDP. CoD, FF and GoB take the heaviest flow in each second; PUBG adds up all its flows.

**`--mode legacy`** reproduces the four original extractors exactly (`new___analyze_COD.py`, `Mich_updt_new___analyze.py`, `new___analyze_GOB.py`, `new___analyze_PUBG.py`). Proof: `features/test_equivalence.py` at commit `4243513` compares both on the same NFStream output, 0 differences on 40 matches (10 per game).

**`--mode standard`** uses one rule set for all games:
- each second gets its own flow's values (fixes problem 1 below),
- PPS and IAT as a rate within the second for every game (problem 2),
- missing seconds are skipped in the decay-weighted mean, as the paper's "null-tolerant windowing" describes (problem 3),
- no PPS filter (problem 6),
- PUBG: only the paper's 184 matches, each balancing run once, and its seconds without an OCR value labelled 145 (Fair), as in the paper's dataset,
- NFStream with one meter, so the output is identical on every run (problem 5).

## Known problems of the original extractors (legacy)

1. **Features misaligned with their second.** The per-second values keep the flow-row index while the output is indexed by second, so second k receives flow row k. In a CoD capture only about 2% of seconds get their own values. PUBG is right until its first second without traffic. The paper's datasets carry this.
2. **GoB computes PPS and IAT as a count** (packets in the 1-second bin); the other games as a rate.
3. **Decay-weighted mean:** CoD, FF and GoB return NaN when any second of the window has no traffic, so the row is dropped later; PUBG skips the missing second.
4. **GoB selects the wrong flow in most seconds:** with all UDP kept, 91% of GoB seconds pick a single-packet flow. Open issue ArielCyber/Gaming-qoe-research-dev#18.
5. **Not deterministic:** NFStream's default parallel meters return slightly different timestamps on each run, so the original output differs run to run (the CoD 10 s dataset rebuilds with 93.6% identical rows). The paper datasets cannot be rebuilt bit for bit, which is why they are frozen here.
6. **`pps < 1000` filter** (from the conference `analyze.py`, 2023, copied into every later extractor). With the rate formula a single-packet second has PPS exactly 1000, so the filter mostly removes single-packet seconds (CoD 2.2%, FF 0.2%, PUBG 3.4%, GoB 91.3%), and also seconds without traffic.

## Standard vs paper results (10 s, three classes, Macro F1)

| Game | RF paper / standard | XGBoost paper / standard |
|---|---|---|
| CoD | 0.899 / 0.886 | 0.901 / 0.883 |
| CoD, five classes | 0.843 / 0.823 | 0.834 / 0.806 |
| Free Fire | 0.879 / 0.869 | 0.857 / 0.813 |
| PUBG | 0.884 / 0.876 | 0.884 / 0.878 |
| GoB | 0.724 / 0.736 | 0.718 / 0.680 |
| Pooled | 0.935 (30 features) / 0.852 (62) | 0.768 / 0.772 |

Decision (2026-11-03): the paper keeps its reported numbers. The standard pipeline is for new work.

## How to run a new test

1. Start from `features/extract.py` and `labels_<game>.csv`, never from an old dataset file.
2. First reproduce the reference at the paper's setting: `--mode legacy` for a paper number, `--mode standard` for the standard baseline above.
3. Change only the one parameter of the test (e.g. `--window`).
4. Train with `training/run_models.py` and compare with the reference.

## Not to use

Student files in the Drive zips that are not part of the paper or the standard (kept on Drive, untouched):
- `dataset_PUBG.csv`, `dataset_Guns_Of_Boom.csv`, michael `window_10_17689…/17696…` (31 columns): the conference 30 features.
- `*_window_size_W_prev_ping.csv` (82 columns): June 2026, add `prev_ping` (the previous second's ping, a label leak), `folder`, bytes.
- `*_new_ficher2_*` (147 columns): June and July 2026, later student work, also with `prev_ping`.
- `dataset_C_O_D.csv` (48 columns), michael `combined_dataset.csv` and `window_10_1770762114.csv` (33 columns): older versions.
- `metadata_cod_fixed.csv`, `test__min_cetchsize_metadata_cod.csv`, michael `runs/*metadata_results*.csv`: label variants not used by the paper.
