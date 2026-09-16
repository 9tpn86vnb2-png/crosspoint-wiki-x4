# CrossPoint Wiki 4.6.4.2 — indexing-speed experiment

Original Xteink X4 / ESP32-C3 ONLY. Application-only firmware, not a merged
flash image. Experimental; not tested on a physical X4 by this build process.

## Scope

This update targets indexing throughput only. Library selection, source identity,
completed-index reuse, article/index/checkpoint formats and the -464.xwi namespace
are unchanged. The 4.6.4.1 guarded file-handle cleanup and HAL assertions remain.

- XML input buffer increases from 8 KiB to 12 KiB, still fixed, independent of
  dump size. A complete sequential scan needs roughly one-third fewer source
  read API calls. Physical SD transaction counts can differ.
- One input-loop visit can process up to eight small work quanta, with a shared
  8 ms time target INCLUDING file reads. It stops at a phase boundary. Previously
  every 8 KiB chunk / 64 merge records forced another complete main-loop visit.
  The absolute scan work cap is 96 KiB per call, not a whole-file allocation.
- Comments, CDATA bodies and processing instructions use bounded span searches
  while retaining NUL rejection and split-delimiter state. Article titles still
  take the existing bounded parsing/normalization path.
- Merge writes reuse the checksum already validated when that unchanged record
  was read. Input and final-output checksum verification remain enabled.
- The indexer translation unit alone uses -O2, with scoped exceptions preserved.
  No global compiler optimization, overclock, SPI clock, HAL or panel waveform
  changes are made.
- The progress badge/bar updates every 10 seconds rather than every 3 seconds;
  stage/pass transitions, pause, completion and errors still request an update.
  This reduces time that indexing is stopped behind the display render lock.
- A measured recent-stage rate is shown: KiB/s for scanning and titles/s for
  sorting/verification. It includes loop, storage and display time. It is not
  a prediction of completion time or a raw SD benchmark. It resets on resume
  and at stage/pass changes.

The importer's fixed object remains under 32 KiB (enforced at compile time).
It does not allocate a whole dump or a vector of all titles. The RAM increase
is approximately 4.3 KiB relative to 4.6.4.1; compiler ABI affects exact size.
Slow SD calls, checkpoint sync and e-ink refresh can exceed the 8 ms target;
this is cooperative scheduling, not a hard real-time guarantee. The normal
single input owner and idle-task yield remain. Full-speed CPU during indexing
was already present; this update does not claim to add it.

## Update without discarding your work

Let an ongoing import finish if practical. Do not reset, remove the SD card,
or flash while it is actively writing. To stop safely, use Back and wait for
PAUSED / checkpoint confirmation, then shut down normally. Back up the SD card,
especially /.crosspoint/, and retain your working 4.6.4.1 binary.

Use your established compatible original-X4 custom APPLICATION update route,
selecting only the .bin. Do not select the ZIP, erase flash, repartition, or
write this application image at address 0x0. A build app0 offset is not proof
of your device's active OTA slot or boot-selection layout.

Keep the XML and its existing indexes/checkpoints in their current paths.
Do not choose Restart import unless you deliberately want to discard partial
work. Build Index/Resume uses the existing checkpoint format. Valid completed
indexes are retained. Recovery after a power cut is not guaranteed against
every SD/filesystem failure; the last accepted checkpoint may precede the
last displayed progress. Normal display progress is less frequent in this build.

## Validation boundary and limits

The release gates compile for ESP32-C3 using PlatformIO CLI and rerun the
real HalStorage.cpp/HalFile host tests (with simulated SD/mutex), including the
intentional invalid-handle assertion control. The 22 archive/index cases and
23 retained algorithm/storage cases run separately. Source fingerprints are
checked across tests and compilation. Host tests are not a hardware emulator.

No hardware speedup multiplier, elapsed-time promise, SD throughput, battery
saving or full compatibility with the user's specific XML is established.
The displayed measured rate is provided to make the next device comparison useful.

Plain decompressed UTF-8 MediaWiki XML only, not .gz/.bz2/.zst. Original XML is
read-only. Initial indexing still scans the whole file and sorts titles on SD.
64-bit APIs do not bypass filesystem limits. Keep spare SD space and power for
large imports. Individual article text remains capped at 32768 raw bytes with
a 256 KiB page-read guard. This is not unlimited-length article pagination.
No font assets, bootloader, partition image or encyclopedia data are distributed.
