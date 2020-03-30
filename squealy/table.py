class Table:
    'A basic table that is the result of a sql query'
    def __init__(self, columns=None, data=None):
        self.columns = columns if columns else []
        self.data = data if data else []
