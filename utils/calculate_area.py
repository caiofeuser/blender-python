import sys
import json

def calculate_area_bb_quick(obj): 
    max_x = obj['max_x']
    min_x = obj['min_x']
    max_y = obj['max_y']
    min_y = obj['min_y']
    w = max_x - min_x
    h = max_y - min_y
    a = w * h 

    print(f'area is: {a}')
    print(f'width: {w} height: {h}')
    return a


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('please provide a correct number of arguments')
    json_string = sys.argv[1]
    try:
        data_obj = json.loads(json_string)
        calculate_area_bb_quick(data_obj)
    except json:
        print("somehting went wrong")
