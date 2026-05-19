# ?ŒìŠ¤???ˆì´?„ì›ƒê³?ê¸°ë³¸ ?¤ìœ„??(Phase 0 ê¸°ì???

## ê¸°ë³¸ `pytest`???¬í•¨?˜ëŠ” ê²½ë¡œ

`pyproject.toml`??`testpaths`ê°€ ?„ë˜ë§??˜ì§‘?œë‹¤. ??ë¬¶ìŒ??CIÂ·ë¡œì»¬??**?„í–‰ ê¸°ì???*?´ë‹¤.

**Git ì¶”ì **: ??ê²½ë¡œ???´ë‹¹?˜ëŠ” ?ŒìŠ¤???Œì¼?€ **?€?¥ì†Œ??ì¶”ì ???íƒœ**?¬ì•¼ ?œë‹¤. `git clone` ì§í›„?ë§Œ `python -m pytest`ë¥??Œë ¸????ê±´ìˆ˜ê°€ ë¬¸ì„œ(?? ??144 passed)?€ ?¬ê²Œ ?´ê¸‹?˜ë©´, ë¡œì»¬ ?„ìš© **ë¯¸ì¶”??* ë³µì‚¬ë³¸ë§Œ ?ˆëŠ”ì§€ ?•ì¸?œë‹¤. ?¹íˆ `tests/unit/`?€ `testpaths`???¬í•¨?˜ë?ë¡?ë¹„ì–´ ?ˆìœ¼ë©????œë‹¤.

- `tests/app/settings/`
- `tests/application/`
- `tests/gui/`
- `tests/infrastructure/`
- `tests/integration/` ??ê³¨ë“  ?¬ë„ˆ??`_archive`ë¡??´ë™?? ?¨ì? ?Œì¼ë§??˜ì§‘
- `tests/unit/` ???„ë©”?¸Â·ì• ?Œë¦¬ì¼€?´ì…˜ ?¨ìœ„ ?ŒìŠ¤???„í–‰ `src` êµ¬ì¡° ?•ë ¬)

## ê¸°ë³¸ ?˜ì§‘?ì„œ ?œì™¸?˜ëŠ” ?ˆê±°??(ì²´í¬ë¦¬ìŠ¤??

2026-04-11 ê°ì‚¬(P0-1) ê¸°ì?. ?¬íŒ… ?°ì„ ?œìœ„???´í›„ ?˜ì´ì¦ˆì—??ê²°ì •?œë‹¤.

| êµ¬ë¶„ | ê²½ë¡œ | ë¹„ê³  |
|------|------|------|
| ???ˆê±°??| `tests/app/test_bootstrap.py`, `tests/app/test_workflows.py` | `app.bootstrap` / `app.workflows` ??ë¯¸ì¡´??ëª¨ë“ˆ |
| ê³µí†µ ?ˆê±°??| `tests/common/test_exception_mapper.py` | `common.*` ?¨í‚¤ì§€ ë¯¸ì¡´??|
| ?„ë©”???ˆê±°??| `tests/domain/` ?„ì²´ | ??`src/domain` ?¨í‚¤ì§€ ?¸ë¦¬?€ ë¶ˆì¼ì¹?|
| ?¸í”„???ˆê±°??| `tests/infra/` ?„ì²´ | `infra.*` ë¯¸ì¡´??|
| ê³¨ë“ Â·?¬ë„ˆ | `tests/_archive/integration/` | `test_golden_scenarios.py`, `run_golden_tests.py` |
| ?¼í¬ë¨¼ìŠ¤ | `tests/_archive/performance/` | `benchmark_*.py`, `benchmark_baseline.json` |

`tests/_archive/`??`norecursedirs`??`_archive` basename???ì–´, `pytest tests`ì²˜ëŸ¼ ?“ê²Œ ?¸ì¶œ?´ë„ ?¬ê??˜ì? ?Šë„ë¡??ˆë‹¤.

## ?¤ëƒ…?·Â·í”½?¤ì²˜

- `tests/snapshots/` ??ê³¼ê±° ?¤ìº” ê²°ê³¼ JSON ?±ì„ ?ê¸° ?„í•œ ?ë¦¬?€?¼ë‚˜, **?„ì¬ ?€?¥ì†Œ?ëŠ” ?Œì¼???†ê±°??ë¹„ì–´ ?ˆì„ ???ˆë‹¤.** [`tests/integration/test_snapshot_normalizer.py`](integration/test_snapshot_normalizer.py)???”ìŠ¤?¬ì˜ JSON???½ì? ?Šê³ , `snapshot_normalizer` ?¬í¼???œì„œÂ·ê²½ë¡œÂ·?€?„ìŠ¤?¬í”„ ?•ê·œ?”ë§Œ ê²€ì¦í•œ??
- `tests/fixtures/` ??ê³ ì • ?°ì´?°ì…‹ ?”ë ‰?°ë¦¬. **ê¸°ë³¸ `pytest` ?¤ìœ„?¸ì—??`tests.fixtures` / `FIXTURES_DIR`ë¥?import?˜ëŠ” ?ŒìŠ¤?¸ëŠ” ?†ë‹¤** (?˜ë™Â·?¥í›„ ?µí•©Â·?„ì¹´?´ë¸Œ ?˜ë„¤?¤ìš©?¼ë¡œ ë³´ê?). ?ì„¸??[fixtures/README.md](fixtures/README.md).

## ê¸°ì???ê°œìˆ˜ ì°¸ê³ 

2026-04-11 ê°ì‚¬?ì„œ???¹ì • 8ê°??Œì¼ë§?ëª¨ì•„ **78 passed**ë¥?ê¸°ë¡?ˆë‹¤. Phase 0 ?´í›„ ê¸°ë³¸ `testpaths`?ëŠ” ?™ì¼ ?Œì¼ ?¸ì— `tests/application`???˜ë¨¸ì§€ ?¤í…Œ?´ì?Â·?Œì´?„ë¼???ŒìŠ¤?¸ì? `tests/unit/` ?„ì²´ê°€ ?¬í•¨?˜ë?ë¡? ë¡œì»¬?ì„œ `python -m pytest`??**??144 passed** ê·œëª¨ê°€ ?œë‹¤(?˜ê²½???°ë¼ ?Œí­ ì°¨ì´ ê°€??.

## ê´€??ë¬¸ì„œ

- ?´ê²° ê³„íš Phase 0: 2026-04-13 local archive bundle
- ê°ì‚¬ ë¦¬í¬??P0-1: 2026-04-13 local archive bundle
## 2026-04-13 cleanup note

- Canonical active filename parser coverage now lives in `tests/unit/test_filename_parser.py`.
- The removed duplicate file `tests/unit/domain/test_filename_parser.py` no longer participates in
  the default suite.
- Disposed legacy tests are no longer kept in the repository worktree; recover them only from the
  2026-04-13 local archive bundle if you explicitly choose to port them.

