
from jtop import jtop


if __name__ == "__main__":

    print("Simple jtop engine reader")

    with jtop() as jetson:
        # jetson.ok() will provide the proper update frequency
        while jetson.ok():
            # Read engines list
            engines = jetson.engine
            # Print all engines
            for engine_name in engines:
                engine = engines[engine_name]
                print("{engine_name} = {engine}".format(engine_name=engine_name, engine=engine))