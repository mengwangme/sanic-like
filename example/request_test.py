from sanic.request import RequestParameters, Request

if __name__ == '__main__':

    args = RequestParameters()
    args['titles'] = ['Post 1', 'Post 2']

    print(args.get('titles'))
    print(args.getlist('titles'))