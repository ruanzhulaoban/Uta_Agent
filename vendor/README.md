# Offline desktop dependencies

This directory is part of the application, not a disposable cache. Include it
in every source ZIP intended for end users. Supported: Windows x64, standard
64-bit CPython 3.10 through 3.14. Other architectures and free-threaded Python
are not supported by this bundle.

`wheels/` contains official PyPI wheels pinned by `requirements-offline.txt`.
Their upstream license texts are preserved inside each wheel and installed
with the packages. `SHA256.json` records checksums. Maintainers can reproduce
the download with `python scripts/prepare_wheels.py` (requires internet and pip).
End users do not run this command: startup installs these local files with
`--no-index` into `.runtime/`, without changing their global Python packages.

`mecab/` contains MeCab 0.996, UTF-8 IPADIC 2.7.0-20070801, and the native
DLL dependency chain. It does not need an MSYS2 installation or system mecabrc.
The wrapper supplies explicit project-local configuration and dictionary paths.
Original license files are in `mecab/licenses/`.

Native binary provenance (from MSYS2's mingw64 distribution):

- mingw-w64-x86_64-mecab 0.996-6
- mingw-w64-x86_64-gcc-libs 16.2.0-3
- mingw-w64-x86_64-libiconv 1.19-1
- mingw-w64-x86_64-libwinpthread 14.0.0.r353.g6df76fa52-2

Upstream/source references:

- MeCab and IPADIC: https://taku910.github.io/mecab/
- MSYS2 packaging recipes and patches: https://github.com/msys2/MINGW-packages
- MSYS2 source package archive: https://repo.msys2.org/mingw/sources/
- GCC: https://gcc.gnu.org/
- GNU libiconv: https://www.gnu.org/software/libiconv/
- mingw-w64: https://www.mingw-w64.org/

Do not distribute `.runtime/`, personal `data/desktop/`, API keys or caches.
The runtime environment is recreated on the recipient's machine. Keep the
provided licenses and upstream notices with redistributions.
