# sections/

The sections [`../reproduce.py`](../reproduce.py) collects: a function `tN` per table or figure of the series,
which prints a header line starting `TN ` and then its rows. [`../docs/SECTIONS.md`](../docs/SECTIONS.md) says
what each section prints, and [`../expected/results.txt`](../expected/results.txt) holds their frozen output.

| Module | Sections |
|---|---|
| [`__init__.py`](__init__.py) | The sections of reproduce.py, one module per part of the series. |
| [`common.py`](common.py) | Constants and helpers that sections of more than one part share. |
| [`part1.py`](part1.py) | Sections of Part 1, a shared signal: T1, T2, T3, T4, T5, T19, T20, T21, T22, T23, T24, T39, T78, T90, T91, T92, T103, T107, T113, T118, T119. |
| [`part2.py`](part2.py) | Sections of Part 2, a shared time scale: T6, T7, T8, T9, T25, T26, T27, T28, T29, T30, T31, T32, T33, T34, T35, T36, T37, T38, T40, T79, T93, T94, T95, T96, T106. |
| [`part3.py`](part3.py) | Sections of Part 3, a shared state: T10, T11, T12, T41, T42, T43, T44, T45, T46, T57, T65, T66, T67, T68, T69, T70, T86, T87, T97, T98, T99, T104, T105, T108. |
| [`part4.py`](part4.py) | Sections of Part 4, a shared assumption: T13, T14, T47, T48, T49, T58, T59, T60, T61, T62, T63, T64, T80, T89, T100, T101, T114. |
| [`part5.py`](part5.py) | Sections of Part 5, a shared order: T15, T16, T50, T51, T52, T71, T72, T76, T77, T82, T83, T84, T85, T102. |
| [`part6.py`](part6.py) | Sections of Part 6, the whole: T17, T18, T53, T54, T55, T56, T73, T74, T75, T81, T88, T109, T110, T111, T112, T115, T116, T117. |
