#!/usr/bin/env python

from __future__ import division
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

VERBOSE = False

def show(s=''):
    print s
def debug(s=''):
    if VERBOSE:
        print '      |  %s' % s
def log(s):
#     print 'LOG: %s' % s
    file(os.path.abspath(config.logFile), 'a').write(s+'\n')

#================================================================================

class Backend(object):
    def __init__(self, bucketName, accessKey, secretKey):
        debug('backend.__init__: connecting to bucket "%s"' % bucketName)
        self.bucketName = bucketName
        self.conn = S3Connection(accessKey, secretKey, host='s3-us-west-2.amazonaws.com')
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
    def uploadBlobFromFile(self, hash, fn, progressPrefix=''):
        debug('backend.uploadBlobFromFile("%s", "%s")' % (hash, fn))
        self.lazyGetBucket()
        k = Key(self.bucket)
        k.key = self.prefix + hash
        def cb(soFar,total):
            # overwrite previous line
            if total == 0:
                pct = 100
            else:
                pct = soFar / total * 100
            sys.stdout.write('\r' + progressPrefix + ' %5.1f %%' % pct + ' '*5)
            sys.stdout.flush()
        k.set_contents_from_filename(fn, cb=cb, encrypt_key=True)
        # blank out the progress line so the next print covers it up
        sys.stdout.write('\r' + ' '*(len(progressPrefix)+10) + '\r')
        sys.stdout.flush()
    def downloadBlobToFile(self, hash, fn, progressPrefix=''):
        debug('backend.downloadBlobToFile("%s", "%s")' % (hash, fn))
        self.lazyGetBucket()
        k = Key(self.bucket)
        k.key = self.prefix + hash
        def cb(soFar,total):
            # overwrite previous line
            if total == 0:
                pct = 100
            else:
                pct = soFar / total * 100
            sys.stdout.write('\r' + progressPrefix + ' %5.1f %%' % pct + ' '*5)
            sys.stdout.flush()
        k.get_contents_to_filename(fn, cb=cb)
        # blank out the progress line so the next print covers it up
        sys.stdout.write('\r' + ' '*(len(progressPrefix)+10) + '\r')
        sys.stdout.flush()
    def printStats(self):
        show('fetching...')
        self.lazyGetBucket()
        bytes = 0
        for key in self.bucket.list():
            bytes += key.size
        monthlyCost = 0.03 * bytes / (1024*1024*1024)
        show()
        show('total data in s3: %s M' % int(bytes / (1024 * 1024)))
        show('                  $ %0.5f / month' % monthlyCost)

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

def createPokeballContents(hash, bytes):
    return 'POKEBALL\n' + str(bytes) + '\n' + hash + '\n'

def getHashFromPokeballFn(pfn):
    lines = file(pfn,'r').readlines()
    assert lines[0].strip() == 'POKEBALL'
    return lines[-1].strip()

def transferAttrs(fn1, fn2):
    fn1stat = os.stat(fn1)
    os.utime(fn2, (fn1stat.st_atime, fn1stat.st_mtime))
    os.chmod(fn2, fn1stat.st_mode)
    # TODO: chown?

def catch(fn, backend, delete=True, recurse=False, progressPrefix=''):
    if not os.path.exists(fn):
        return
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
    bytes = os.path.getsize(fn)
    pokeballContents = createPokeballContents(hash, bytes)
    if not backend.hasBlob(hash):
        backend.uploadBlobFromFile(hash, fn, progressPrefix=progressPrefix)
    log('%s catch %s %s' % (int(time.time()*1000), hash, os.path.abspath(fn)))
    pfn = pokeballifyFilename(fn)
    file(pfn, 'w').write(pokeballContents)
    transferAttrs(fn, pfn)
    if delete:
        os.unlink(fn)

def release(fn, backend, delete=True, recurse=False, progressPrefix=''):
    if not os.path.exists(fn):
        return
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
    # download to a temp file, transfer attrs, then rename into place
    tempfn = fn + '__TEMP'
    try:
        backend.downloadBlobToFile(hash, tempfn, progressPrefix=progressPrefix)
        transferAttrs(pfn, tempfn)
        os.rename(tempfn, fn)
    finally:
        # make sure temp file gets deleted (for example, from a control-C during upload)
        if os.path.exists(tempfn):
            os.unlink(tempfn)
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

    pokedex stats

        Show the total size of data in s3.

    pokedex help

    flags:
        -r --recurse
        -n --no-delete
        -v --verbose
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
VERBOSE = '-v' in FLAGS or '--verbose' in FLAGS

if '-h' in FLAGS or '--help' in FLAGS:
    showHelpAndQuit()
if CMD not in ['catch', 'release', 'stats']:
    showHelpAndQuit()

#--------------------------------------------------------
# catch

backend = Backend(config.bucketName, config.accessKey, config.secretKey)

if CMD == 'catch':
    if not ARGS: showHelpAndQuit()
    # remove the pokeballs in advance to help us get a more accurate progress bar count
    ARGS = [a for a in ARGS if not isPokeballFilename(a)]
    for ii,fn in enumerate(ARGS):
        # remove trailing slashes
        if fn.endswith('/') and fn != '/': fn = fn[:-1]
        progressPrefix = '%s/%s    ' % (ii, len(ARGS))
        catch(fn, backend, delete=(not NO_DELETE), recurse=RECURSE, progressPrefix=progressPrefix)

if CMD == 'release':
    if not ARGS: showHelpAndQuit()
    for ii,fn in enumerate(ARGS):
        # remove trailing slashes
        if fn.endswith('/') and fn != '/': fn = fn[:-1]
        progressPrefix = '%s/%s    ' % (ii, len(ARGS))
        release(fn, backend, delete=(not NO_DELETE), recurse=RECURSE, progressPrefix=progressPrefix)

if CMD == 'stats':
    backend.printStats()

quit()

#
