import pandas as pd
import matplotlib.pyplot as plt
import argparse
from matplotlib.font_manager import FontProperties


def main():
    pd.set_option("display.max_rows", 10, "display.max_columns", None)
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_data_file_path", type=str, help="enter path to raw data as argument")
    args = parser.parse_args()

    df = pd.read_csv(args.raw_data_file_path)

    # -- data preprocessing --
    # add sample column
    df['sample'] = df.index + 1
    df['sample'] = df['sample'] * 0.5

    # convert freq from kHz to MHz
    df.loc[:, 'CPU1freq'] = df.loc[:, 'CPU1freq'] / 1000
    df.loc[:, 'CPU2freq'] = df.loc[:, 'CPU2freq'] / 1000
    df.loc[:, 'CPU3freq'] = df.loc[:, 'CPU3freq'] / 1000
    df.loc[:, 'CPU4freq'] = df.loc[:, 'CPU4freq'] / 1000
    df.loc[:, 'CPU5freq'] = df.loc[:, 'CPU5freq'] / 1000
    df.loc[:, 'CPU6freq'] = df.loc[:, 'CPU6freq'] / 1000
    df.loc[:, 'GPU_FREQ'] = df.loc[:, 'GPU_FREQ'] / 1000

    cols_to_drop = ['MTS FG', 'MTS BG', 'RAM', 'EMC', 'SWAP', 'APE', 'NVENC', 'NVDEC', 'NVJPG', 'fan', 'power cur',
                    'jetson_clocks', 'power avg', 'uptime']

    df.drop(columns=cols_to_drop, inplace=True)

    # print columns
    print("columns: ", df.columns)

    # graphs
    font1 = {'family': 'serif', 'color': 'black', 'size': 9}
    font2 = {'family': 'serif', 'color': 'darkred', 'size': 15}

    fig = plt.figure()
    fig.set_figheight(3)
    fig.set_figwidth(4.5)
    ax1 = plt.subplot2grid(shape=(5, 3), loc=(0, 0), colspan=3)
    ax2 = plt.subplot2grid(shape=(5, 3), loc=(1, 0), colspan=3)
    ax3 = plt.subplot2grid(shape=(5, 3), loc=(2, 0), colspan=3)
    ax4 = plt.subplot2grid(shape=(5, 3), loc=(3, 0), colspan=3)
    ax5 = plt.subplot2grid(shape=(5, 3), loc=(4, 0), colspan=3)

    # core temp graphs
    ax1.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'Temp AO'].astype(float), label='AO')
    ax1.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'Temp AUX'].astype(float), label='AUX')
    ax1.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'Temp CPU'].astype(float), label='CPU')
    ax1.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'Temp GPU'].astype(float), label='GPU')
    ax1.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'Temp thermal'].astype(float), label='thermal')
    fontP = FontProperties()
    fontP.set_size('xx-small')
    ax1.legend(loc=1, ncol=1, bbox_to_anchor=(0, 0, 1, 1),
               prop=fontP, fancybox=True, shadow=False, title=None)
    ax1.set_title('Temperature vs time', fontdict=font1)
    ax1.set_ylabel('temp (˚C)')

    ax1.grid(color='green', linestyle='--', linewidth=0.5)
    ax1.set_ylim([-1, 109])
    ax1.axes.get_xaxis().set_ticklabels([])

    # cpu usage vs time graph
    ax2.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU1'].astype(float), label='core1')
    ax2.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU2'].astype(float), label='core2')
    ax2.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU3'].astype(float), label='core3')
    ax2.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU4'].astype(float), label='core4')
    ax2.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU5'].astype(float), label='core5')
    ax2.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU6'].astype(float), label='core6')
    ax2.legend(loc=1, ncol=1, bbox_to_anchor=(0, 0, 1, 1),
               prop=fontP, fancybox=True, shadow=False, title=None)
    ax2.set_title('CPU-core(% used) vs time', fontdict=font1)
    ax2.set_ylabel('CPU-core(% used)')

    ax2.grid(color='green', linestyle='--', linewidth=0.5)
    ax2.set_ylim([-1, 109])
    ax2.axes.get_xaxis().set_ticklabels([])

    # CPU core freq vs sample
    ax3.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU1freq'].astype(float), label='core1')
    ax3.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU2freq'].astype(float), label='core2')
    ax3.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU3freq'].astype(float), label='core3')
    ax3.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU4freq'].astype(float), label='core4')
    ax3.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU5freq'].astype(float), label='core5')
    ax3.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'CPU6freq'].astype(float), label='core6')
    ax3.legend(loc=1, ncol=1, bbox_to_anchor=(0, 0, 1, 1),
               prop=fontP, fancybox=True, shadow=False, title=None)
    ax3.set_title('CPU-core freq vs time', fontdict=font1)
    ax3.set_ylabel('CPU-freq(MHz)')

    ax3.grid(color='green', linestyle='--', linewidth=0.5)
    ax3.axes.get_xaxis().set_ticklabels([])

    # GPU (% used) vs sample
    ax4.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'GPU'].astype(float), label='GPU')
    ax4.legend(loc=1, ncol=1, bbox_to_anchor=(0, 0, 1, 1),
               prop=fontP, fancybox=True, shadow=False, title=None)
    ax4.set_title('GPU (% used) vs time', fontdict=font1)
    ax4.set_ylabel('GPU (% used)')
    ax4.grid(color='green', linestyle='--', linewidth=0.5)
    ax4.set_ylim([-1, 109])
    ax4.axes.get_xaxis().set_ticklabels([])

    # GPU freq
    ax5.plot(df.loc[:, 'sample'].astype(float), df.loc[:, 'GPU_FREQ'].astype(float), label='GPU_FREQ')
    ax5.legend(loc=1, ncol=1, bbox_to_anchor=(0, 0, 1, 1),
               prop=fontP, fancybox=True, shadow=False, title=None)
    ax5.set_title('GPU freq', fontdict=font1)
    ax5.set_ylabel('GPU freq (MHz)')
    ax5.grid(color='green', linestyle='--', linewidth=0.5)
    ax5.set_xlabel('time(s)')

    # display plots
    plt.suptitle("Jtop Plots - Thermal Chamber at Room temperature", fontdict=font2)
    plt.show()


if __name__ == "__main__":
    main()
