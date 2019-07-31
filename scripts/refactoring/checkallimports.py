import importscan

to_check = 'cfme artifactor fixtures markers utils'

if __name__ == '__main__':
    for name in to_check.split():
        base = __import__(name)

        def handle_error(name, error):
            print(name, error)
        importscan.scan(base, handle_error=handle_error)
