# blasefs - the blaseball filesystem

## Setup
Install requirements (`pip install -r requirements.txt`)  
Installation may require `libfuse-dev` or similar installed, to compile the `fuse-python` package.  

## Usage
`python blasefs.py <mountpoint>`

## Caveats
Currently only generates 'files' for historical games, not current season games, or scheduled games.  
Almost filesystem operations trigger a number of API calls to Chronicler, please use responsibly.

## Thanks
Huge thanks to everyone from [SIBR](https://sibr.dev/), especially those who work on Chronicler.  
Thanks in particular to [blaseball-mike](https://github.com/jmaliksi/blaseball-mike/), without which these
crimes would not have been possible.  

Created for https://cursed.sibr.dev/
