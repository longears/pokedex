Pokedex
=======

A way to shrink down files when you don't need them.

*This is alpha code!  It might lose your precious data!*

**Uploading files**

When your laptop is almost out of space, squeeze some files into pokeballs:

```
$ pokedex catch myfile.psd
```

...Which will upload the file to S3.  It then deletes the local copy and replaces it with tiny placeholder file called `myfile.psd__pokeball`.

**Getting them back**

The pokeball file contains the hash of the file so that we can get it back later, by doing this:

```
$ pokedex release myfile.psd__pokeball
```

...Which downloads the file from S3 again.

Other commands:

```
$ pokedex cost  // show the cost of current storage used on S3
$ pokedex du    // add up the disk space used inside the pokeballs here
```

Installation
------------

1. Sign up for S3, create a bucket there, and get its access key and secret key.
1. Install `boto` (the Python library for Amazon Web Services) by running `sudo pip install boto`
1. In the Pokedex code, copy `config.py.example` to `config.py` and fill out the variables inside it.
1. Add `pokedex.py` to your $PATH.

Use cases
---------

Pokeball files are tiny and easy to send to other computers, if you already have Pokedex set up and configured there.

Dropbox almost full?  Squash some files down into pokeballs.  Use Dropbox as a repository of pokeball files.

Your laptop is almost full and you need to shift some stuff off of it for a while.

Technical details
-----------------

On S3, files are stored by their hash to prevent duplication.  This also means it's very fast to catch a file if it's already on S3.  There's currently no way to delete things from S3 because who knows what pokeballs you might have sitting around somewhere.

There's no central repository of filenames or metadata.  The pokeball files act as local carriers of that information, so don't lose them.  For now there's also a log being written to `{$HOME}/.pokedex_log` to help match filenames to hashes in case of disasters.

A pokeball file looks like this (minus the comments).
```
POKEBALL     // a magic phrase to help us identify pokeballs
492          // number of bytes in the original file
sha256_7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730
             // the hash of the file contents
```

To do
-----

* Hash and upload files in chunks for better deduplication and for resumability
* Command line flag parsing could be more robust
* Write tests
* Make a file-based backend
* Sync between backends
* FUSE filesystem that displays pokeballs as real files, fetched on demand

