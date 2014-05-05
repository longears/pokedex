#!/usr/bin/env python

import hashlib
import os
import sys
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import config

"""
poke-catch file [file file ...]
poke-release file [file file ...]

foo.txt --> foo.txt__pokeball

pokeball contents:

    POKEBALL
    sha1-oifjqofijq3ofiq3f34
    sha1-942f298dh298qhd9q8h
    sha1-afiq34fjq3o4fiq3j4f

a pokeball keeps all the same file metadata (dates, etc) as the original.
"""

def debug(s):
    print '        %s' % s
def show(s):
    print s

#================================================================================

class Backend(object):
    def __init__(self, bucketName, accessKey, secretKey):
        debug('backend.__init__: connecting to bucket "%s"' % bucketName)
        self.bucketName = bucketName
        self.conn = S3Connection(accessKey, secretKey)
        self.bucket = self.conn.get_bucket(self.bucketName)
        self.prefix = 'blobs/'
    def hasBlob(self, hash):
        debug('backend.hasBlob("%s")' % hash)
        key = self.prefix + hash
        return bool(self.bucket.get_key(key))
    def uploadBlobFromFile(self, hash, fn):
        debug('backend.uploadBlobFromFile("%s", "%s")' % (hash, fn))
        k = Key(self.bucket)
        k.key = self.prefix + hash
        k.set_contents_from_filename(fn)
    def downloadBlobToFile(self, fn):
        # TODO: not tested
        debug('backend.downloadBlobToFile("%s")' % fn)
        k = Key(self.bucket)
        k.key = self.prefix + hash
        k.get_contents_to_filename(fn)

#================================================================================

def pokeballifyFilename(fn):
    return fn + '__pokeball'

def unpokeballifyFilename(pfn):
    assert isPokeballFilename(pfn)
    return pfn.rsplit('__pokeball', 1)[0]

def isPokeballFilename(pfn):
    return pfn.endswith('__pokeball')

def getFileHash(fn):
    data = file(fn, 'rb').read()
    return 'sha256_' + hashlib.sha256(data).hexdigest()

def createPokeballContents(hash):
    return 'POKEBALL\n' + hash + '\n'

def writePokeballAndTransferAttrs(fn, pfn, pokeballContents):
    # TODO: set modtime and permissions on pfn to match fn
    file(pfn,'w').write(pokeballContents)

def catch(fn, backend, delete=True):
    debug('catch("%s")' % fn)
    hash = getFileHash(fn)
    pokeballContents = createPokeballContents(hash)
    if not backend.hasBlob(hash):
        backend.uploadBlobFromFile(hash, fn)
    pfn = pokeballifyFilename(fn)
    writePokeballAndTransferAttrs(fn, pfn, pokeballContents)
    if delete:
        os.unlink(fn)

def release(fn, backend):
    pass

#================================================================================
# MAIN

show('-----------------------------------------------------------------\\')
def quit():
    show('-----------------------------------------------------------------/')
    sys.exit(0)
def showHelpAndQuit():
    show("""
usage:
    pokedex catch [flags] file [file2 file3 ...]
    pokedex release [flags] file [file2 file3 ...]
    pokedex help

    flags:
        -r --recurse
        -n --no-delete
    """)
    quit()

ARGS = sys.argv[1:]
if len(ARGS) == 0:
    showHelpAndQuit()

CMD = ARGS[0]
ARGS = ARGS[1:]
FLAGS = [x for x in ARGS if x.startswith('-')]
ARGS = [x for x in ARGS if not x.startswith('-')]

RECURSE = '-r' in FLAGS or '--recurse' in FLAGS
NO_DELETE = '-n' in FLAGS or '--no-delete' in FLAGS

if '-h' in FLAGS or '--help' in FLAGS:
    showHelpAndQuit()
if CMD not in ['catch', 'release']:
    showHelpAndQuit()

if CMD == 'catch':
    backend = Backend(config.bucketName, config.accessKey, config.secretKey)
    for fn in ARGS:
        show('catching %s' % fn)
        catch(fn, backend, delete = not NO_DELETE)
    show('done')

quit()

#
