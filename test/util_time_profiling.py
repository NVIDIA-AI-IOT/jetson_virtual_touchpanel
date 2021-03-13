# Copyright (c) 2020-2021, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import wraps
import time
import queue

class TimeIt:
    q = queue.Queue()

    @classmethod
    def measure(cls, func) :
        q = cls.q

        @wraps(func)
        def wrapper(*args, **kargs) :
            start_time = int(round(time.time() * 1000))
            result = func(*args,**kargs)
            elapsed_time = int(round(time.time() * 1000)) - start_time
            q.put((func.__name__, elapsed_time))
            return result

        return wrapper
    
    @classmethod
    def show_result(cls, main_func, sub_funcs=None):
        q = cls.q

        while not q.empty():
            func_name, time = q.get()
            if func_name == main_func.__name__ :
                print("-------------------------------")
                format_str = "  {:<14}: {:>3} (ms) ==> {:.1f} fps"
                print(format_str.format(func_name, time, 1000.0/time) )
            else:
                format_str = "  {:<14}: {:>3} (ms)"
                print(format_str.format(func_name, time) )

        print("======================================")
