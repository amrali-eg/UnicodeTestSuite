"""Unicode Test Suite Generator (UTS) - core package.

This package contains every module used to build the deterministic
encoding-test corpus produced by GenerateCorpus.py. Nothing in this
package depends on anything outside the Python 3.11 standard library.
"""

# Bump this whenever the generation logic (documents, encodings, layout,
# or filename scheme) changes in a way that would alter the corpus output.
GENERATOR_VERSION = "3.0.0"

# Schema version for Manifest.csv / Manifest.sqlite / MasterHashes.sha256.
# Bump on any change to the manifest columns, the MasterHashes coverage
# set, or the certificate fields, so consumers can detect the shape of
# the corpus they are reading. Recorded in CorpusCertificate.txt, in the
# `meta` table of Manifest.sqlite, and in ManifestVersion.txt.
MANIFEST_VERSION = "3.0"
