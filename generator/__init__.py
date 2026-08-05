"""Unicode Test Suite Generator (UTS) - core package.

This package contains every module used to build the deterministic
encoding-test corpus produced by GenerateCorpus.py. Nothing in this
package depends on anything outside the Python 3.11 standard library.
"""

# Bump this whenever the generation logic (documents, encodings, layout,
# or filename scheme) changes in a way that would alter the corpus output.
GENERATOR_VERSION = "2.0.0"
