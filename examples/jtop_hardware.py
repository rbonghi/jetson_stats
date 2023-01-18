
from jtop import jtop


if __name__ == "__main__":

    print("Simple jtop hardware reader")

    with jtop() as jetson:
        # jetson.ok() will provide the proper update frequency
        if jetson.ok():
            # Read hardware, platform and libraries list
            # Print all values
            for name_category, category in jetson.board.items():
                print("{name}:".format(name=name_category))
                # Print all category
                for name, value in category.items():
                    print(" - {name}: {value}".format(name=name, value=value))
# EOF
