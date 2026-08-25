import sys
import os


BASE=os.path.dirname(
os.path.dirname(
os.path.abspath(__file__)
)
)


sys.path.insert(
0,
BASE
)


from service.result_update import update_result

from service.rank_generate import generate_rank



def run():


    print(
    "开始每日统计"
    )


    update_result()


    generate_rank()



    print(
    "每日统计完成"
    )



if __name__=="__main__":

    run()

