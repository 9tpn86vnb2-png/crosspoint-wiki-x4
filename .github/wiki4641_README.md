# CrossPoint Wiki 4.6.4.1 — file-handle crash hotfix

Original Xteink X4 / ESP32-C3 ONLY. Experimental, not tested on a physical X4.
Application image; not a full-flash/bootloader/partition image.

## Corrected defect

4.6.4's WikiIndexJob::begin() first called closeFiles() on its five default-constructed
HalFile members. Their implementation pointers were null. Real HalFile::close()
asserts impl != nullptr at HalStorage.cpp:252. Destruction, early failures and
first merge preparation had the same lifetime problem. This can trigger with
small XML files too; it does not demonstrate a 2 GB or 2.5 GB size ceiling.

The old host adapter accepted close() on an empty handle. Those prior host results
did not test the real device HAL ownership semantics and missed this defect.

This hotfix guards all 21 indexer close-call sites and the archive's beginIndex
cleanup. It does NOT disable or weaken any HAL assertion, and does not change
buffer sizes, offsets, indexing/sorting algorithms, checkpoint or index formats,
UI layout, filesystem/bootloader, or other reader features. Display and SDK
version are 1.6.0-wiki-4.6.4.1.

## Installation and retry

Back up /.crosspoint/ and retain a known-working firmware. Use the same compatible
original-X4 custom APPLICATION update route as before, selecting only the .bin.
Do not erase flash, repartition, or write the application image at address 0x0.
For CLI flashing, use only the application slot/offset already verified for your
particular installed layout. The build's app0 offset is 0x10000; that does not
establish your active OTA slot or boot selection.

Keep the original XML and existing index/checkpoint files. No folder deletion or
card reformat is required for this fix. Open the same XML through Wikipedia and
choose Build Index/Resume. Back pauses; Confirm resumes. The -464.xwi and .search
namespace and the 4.6.4 checkpoint format are intentionally unchanged.

Start with a small XML, then retry the 2.5 GB file. The previous startup crash
may have prevented any checkpoint from being written, so indexing may begin at
0%. Do not promise full recovery if the prior SD write was interrupted.

If it crashes again, retain the full crash_report.txt, version, stack/backtrace,
last logs and indexing phase/progress. Avoid repeatedly starting an import that
crashes; use your established recovery route or known-working firmware.

## Validation

The new harness compiles production lib/hal/HalStorage.cpp and HalStorage.h, plus
the real archive/indexer/search code. Only the SD driver and recursive mutex are
host adapters. It reproduces the old exact line-252 assertion, then exercises
30 successful cases and one deliberate assertion control after the fix, under
AddressSanitizer and UndefinedBehaviorSanitizer. The control ensures invalid raw
HalFile use STILL asserts rather than hiding errors. See the JSON reports.
Existing 22 archive/index tests and 23 retained algorithm/storage cases are run
separately. Their version labels still refer to the inherited suite, not the
firmware's version. Production source hashes are checked before/after testing.

Actual ESP32-C3 CLI compilation, image checks, slot-fit checks and version checks
are release gates. Compiler/tests do not certify hardware operation. No physical
X4, your XML, SD throughput, battery use or display timing was tested here.

## Unchanged 4.6.4 limits

Plain decompressed UTF-8 MediaWiki XML, not compressed .gz/.bz2/.zst. SD-backed
article offsets and title sort index; 8 KiB scan chunks. Initial import remains
a full scan and disk sort. 64-bit APIs do not override filesystem/card limits.
Individual article raw text remains capped at 32768 bytes with a 256 KiB page-read
guard. This hotfix does not add unlimited-length article pagination. Allow spare
SD space for indexes, sorting and checkpoints. Keep power connected during long
imports and do not remove the SD card while it is working.

No font files or encyclopedia data are included.
