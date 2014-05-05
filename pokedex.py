#!/usr/bin/env python

import hashlib
import os
import sys
import time

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

def show(s=''):
    print s
def debug(s=''):
    pass
#     print '      |  %s' % s
def log(s):
#     print 'LOG: %s' % s
    file(os.path.abspath(config.logFile), 'a').write(s+'\n')

#================================================================================

class Backend(object):
    def __init__(self, bucketName, accessKey, secretKey):
        debug('backend.__init__: connecting to bucket "%s"' % bucketName)
        self.bucketName = bucketName
        self.conn = S3Connection(accessKey, secretKey)
        self.bucket = None
        self.prefix = 'blobs/'
    def lazyGetBucket(self):
        if not self.bucket:
            self.bucket = self.conn.get_bucket(self.bucketName)
    def hasBlob(self, hash):
        debug('backend.hasBlob("%s")' % hash)
        self.lazyGetBucket()
        key = self.prefix + hash
        return bool(self.bucket.get_key(key))
    def uploadBlobFromFile(self, hash, fn):
        debug('backend.uploadBlobFromFile("%s", "%s")' % (hash, fn))
        self.lazyGetBucket()
        k = Key(self.bucket)
        k.key = self.prefix + hash
        k.set_contents_from_filename(fn)
    def downloadBlobToFile(self, hash, fn):
        # TODO: not tested
        debug('backend.downloadBlobToFile("%s", "%s")' % (hash, fn))
        self.lazyGetBucket()
        k = Key(self.bucket)
        k.key = self.prefix + hash
        k.get_contents_to_filename(fn)

#================================================================================

def pokeballifyFilename(fn):
    return fn + config.pokeballSuffix

def unpokeballifyFilename(pfn):
    assert isPokeballFilename(pfn)
    return pfn.rsplit(config.pokeballSuffix, 1)[0]

def isPokeballFilename(pfn):
    return pfn.endswith(config.pokeballSuffix)

def getFileHash(fn):
    data = file(fn, 'rb').read()
    return 'sha256_' + hashlib.sha256(data).hexdigest()

def createPokeballContents(hash):
    return 'POKEBALL\n' + hash + '\n'

def getHashFromPokeballFn(pfn):
    lines = file(pfn,'r').readlines()
    return lines[-1].strip()

def transferAttrs(fn1, fn2):
    # TODO
    pass

def catch(fn, backend, delete=True, recurse=False):
    if os.path.isdir(fn):
        if not recurse:
            show(' skipping dir: %s' % fn)
            return
        subs = [os.path.join(fn, s) for s in os.listdir(fn)]
        subfiles = [s for s in subs if os.path.isfile(s)]
        subdirs = [s for s in subs if os.path.isdir(s)]
        debug('  is a directory.  recursing on files...')
        for subfile in subfiles:
            catch(subfile, backend, delete, recurse)
        debug('  recursing on directories...')
        for subdir in subdirs:
            catch(subdir, backend, delete, recurse)
        return
    if isPokeballFilename(fn): return
    if os.path.islink(fn):
        show('skipping link: %s' % fn)
        return
    if not os.path.isfile(fn):
        show('skipping strange non-file: %s' % fn)
        return

    # normal single-file catching
    show('     catching: %s' % fn)
    hash = getFileHash(fn)
    pokeballContents = createPokeballContents(hash)
    if not backend.hasBlob(hash):
        backend.uploadBlobFromFile(hash, fn)
    log('%s catch %s %s' % (int(time.time()*1000), hash, os.path.abspath(fn)))
    pfn = pokeballifyFilename(fn)
    file(pfn, 'w').write(pokeballContents)
    transferAttrs(fn, pfn)
    if delete:
        os.unlink(fn)

def release(fn, backend, delete=True, recurse=False):
    if os.path.isdir(fn):
        if not recurse:
            show(' skipping dir: %s' % fn)
            return
        subs = [os.path.join(fn, s) for s in os.listdir(fn)]
        subfiles = [s for s in subs if os.path.isfile(s)]
        subdirs = [s for s in subs if os.path.isdir(s)]
        debug('  is a directory.  recursing on files...')
        for subfile in subfiles:
            release(subfile, backend, delete, recurse)
        debug('  recursing on directories...')
        for subdir in subdirs:
            release(subdir, backend, delete, recurse)
        return
    if not isPokeballFilename(fn): return
    if os.path.islink(fn):
        show('skipping link: %s' % fn)
        return
    if not os.path.isfile(fn):
        show('skipping strange non-file: %s' % fn)
        return

    # normal single-file releasing
    pfn = fn
    show('     releasing: %s' % pfn)
    hash = getHashFromPokeballFn(pfn)
    fn = unpokeballifyFilename(pfn)
    backend.downloadBlobToFile(hash, fn)
    transferAttrs(pfn, fn)
    if delete:
        os.unlink(pfn)

#================================================================================
# MAIN

show('-----------------------------------------------------------------\\')
def quit():
    show('-----------------------------------------------------------------/')
    sys.exit(0)
def showHelpAndQuit():
    show("""
usage:
    pokedex catch [-r | -n] file [file2 file3 ...]

        Upload the files to s3 and replace them with pokeball files.
        Delete the original after upload unless -n is set.
        Ignores directories unless -r is set.

    pokedex release [-r] file [file2 file3 ...]

        Given a list of pokeball files, replace them by downloading the original data.
        Ignores directories unless -r is set.

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

#--------------------------------------------------------
# catch

if CMD == 'catch':
    if not ARGS: showHelpAndQuit()
    backend = Backend(config.bucketName, config.accessKey, config.secretKey)
    for fn in ARGS:
        # remove trailing slashes
        if fn.endswith('/') and fn != '/': fn = fn[:-1]
        catch(fn, backend, delete = not NO_DELETE, recurse = RECURSE)

if CMD == 'release':
    if not ARGS: showHelpAndQuit()
    backend = Backend(config.bucketName, config.accessKey, config.secretKey)
    for fn in ARGS:
        # remove trailing slashes
        if fn.endswith('/') and fn != '/': fn = fn[:-1]
        release(fn, backend, delete = not NO_DELETE, recurse = RECURSE)

quit()

#
