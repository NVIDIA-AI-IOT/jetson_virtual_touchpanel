###
### https://dev.classmethod.jp/articles/method-to-parallel-processes-with-pipeline/
### 

from functools import wraps
from operator import attrgetter
import time

class TimeMeasure:
    time_result = {}

    @classmethod
    def stop_watch(cls, func) :
        time_result = cls.time_result

        @wraps(func)
        def wrapper(*args, **kargs) :
            start = time.time()
            result = func(*args,**kargs)
            elapsed_time =  time.time() - start

            if not func.__name__ in time_result:
                time_result[func.__name__] = []
            time_result[func.__name__].append(elapsed_time)

            return result

        return wrapper

    @classmethod
    def show_time_result(cls, main_func, sub_funcs=None):
        time_result = cls.time_result

        main_func_name = main_func.__name__
        time_func = sum(time_result[main_func_name])
        print("{}: {:.3f}[s]={:.1f}[fps]".format(main_func_name, time_func, 1.0/time_func))

        if sub_funcs is None:
            sub_func_names = set(time_result.keys()) - set([main_func.__name__])
        else:
            sub_func_names = list(map(lambda func: func.__name__, sub_funcs))

        max_len_names = max(map(lambda name: len(name), sub_func_names))

        for sub_func_name in sub_func_names:
            time_func = sum(time_result[sub_func_name])
            format_str = "  {:<" + str(max_len_names) + "}: {:.3f}[s]"
            print(format_str.format(sub_func_name, time_func) )

    @classmethod
    def reset_time_result(cls):
        time_result = cls.time_result
        time_result.clear()
