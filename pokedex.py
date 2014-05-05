#!/usr/bin/env python

import hashlib
import os
from boto.s3.connection import S3Connection
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

class Backend(object):
    def __init__(self, accessKey, secretKey):
        self.conn = S3Connection(accessKey, secretKey)
    def hasBlob(self, hash): pass
    def uploadBlobFromFile(self, hash, fn): pass
    def downloadBlobToFile(self, fn): pass

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

def createPokeballContents(fn):
    return 'POKEBALL\n' + getFileHash(fn)

def catch(fn, backend):
    pokeballContents = createPokeballContents(fn)
    hash = pokeballContents.splitlines()[1]
    backend.uploadBlobFromFile(hash, fn)
    pfn = pokeballifyFilename(fn)
    file(pfn,'w').write(pokeballContents)
    os.unlink(fn)


def release(fn, backend):
    pass



backend = Backend(config.accessKey, config.secretKey)
catch('./test', backend)





#
