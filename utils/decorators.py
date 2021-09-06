from functools import wraps

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response


def required_params(method='GET', params=None):
    """
    检查是否有 param 缺失

    当我们使用 @required_params(params=['some_param']) 的时候
    这个 required_params 函数应该需要返回一个 decorator 函数，这个 decorator 函数的参数的内容
    就是被 @required_params 包裹起来的函数 view_func
    """

    # GET: request.query_params
    # 其余 POST/PUT/DELETE/PATCH: request.data

    # 从效果上来说，参数中写 params=[] 很多时候也没有太大问题
    # 但是从好的编程习惯上来说，函数的参数列表中的值不能是一个 mutable 的参数
    if params is None:
        params = []

    def decorator(view_func):
        """
        decorator 函数通过 wraps 来将 view_func 里的参数解析出来传递给 _wrapped_view
        这里的 instance 参数其实就是在 view_func 里的 self
        """

        @wraps(view_func)
        def _wrapped_view(instance, request: Request, *args, **kwargs):
            # data = getattr(request, request_attr)  # 从 request 中取出 request_attr 中参数
            if method.lower() == 'get':
                data = request.query_params
            else:
                data = request.data

            missing_params = [
                param
                for param in params
                if param not in data
            ]
            if missing_params:
                params_str = ','.join(missing_params)
                return Response({
                    'message': 'missing {} in request'.format(params_str),
                    'success': False,
                }, status=status.HTTP_400_BAD_REQUEST)

            # 做完检测之后，再去调用被 @required_params 包裹起来的 view_func
            return view_func(instance, request, *args, **kwargs)

        return _wrapped_view

    return decorator