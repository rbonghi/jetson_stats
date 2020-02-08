

from jtop import jtop


with jtop() as jetson:
    if 'SWAP' in jetson.stats:
        print(jetson.stats['SWAP'])
    # swap
    jetson.swap.enable = True
    # 
    if 'SWAP' in jetson.stats:
        print(jetson.stats['SWAP'])