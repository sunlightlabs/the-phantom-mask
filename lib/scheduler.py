import concurrent.futures
from Queue import Queue

queue = Queue()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


