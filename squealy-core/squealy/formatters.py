
class Formatter:
    def supports_multi_queries(self):
        return False

    def format(self, prev_results, query, table):
        '''Format a table, combine it with the results from previous queries, and return the new result
        
        prev_results is the combined results of all previous queries. It can be None, a list or a dictionary
        Most formatters only handle a single query. In such a case, results will be None

        query is the current query that produced the table
        table is the output of the current query that needs to be formatted
        '''
        pass

class SimpleFormatter(Formatter):
    def format(self, prev_results, query, table):
        data = {"columns": table.columns, "data": table.data}
        return data

class JsonFormatter(Formatter):
    def __init__(self, envelope="data"):
        self.envelope = envelope

    def supports_multi_queries(self):
        return True

    def _add_envelope(self, obj):
        return {self.envelope: obj}
    
    def _remove_envelope(self, obj):
        return obj[self.envelope]

    def format(self, prev_results, query, table):
        if prev_results:
            prev_results = self._remove_envelope(prev_results)
        
        result = table.as_dict()
        if query.is_object:
            result = result[0]

        if query.is_root:
            return self._add_envelope(result)
        elif isinstance(prev_results, dict) or prev_results is None:
            if prev_results is None:
                prev_results = {}
            prev_results[query.key] = result
            return self._add_envelope(prev_results)
        elif isinstance(prev_results, list):
            assert query.is_list
            self._merge_lists(prev_results, result, query.merge, query.key)
            return self._add_envelope(prev_results)
        else:
            raise Exception("Should not come here")

    def _merge_lists(self, parent_list, child_list, merge, key):
        for parent in parent_list:
            primary_key = parent[merge['parent']]
            children = [c for c in child_list if c[merge['child']] == primary_key]
            parent[key] = children

class SeriesFormatter(Formatter):
    def supports_multi_queries(self):
        return False

    def _transpose(self, table):
        transposed = {}
        for colnum, colname in enumerate(table.columns):
            series = []
            for row in table.data:
                series.append(row[colnum])
            transposed[colname] = series
        return transposed

    def format(self, prev_results, query, table):
        transposed = self._transpose(table)
        return {"data": transposed}


class GoogleChartsFormatter(Formatter):
    def _generate_chart_data(self, table, column_types):
        """
        Converts the query response to data format desired by google charts
        Google Charts Format ->
        {
          rows: [
            "c":
              [
                {
                  "v": series/x-axis label name,
                  "v": value
                },
              ], ...
            ],
            cols: [
              {
                "label": Column name,
                "type": data type for the column
              }
            ]
        }
        """
        response = {}
        response['rows'] = rows = []
        response['cols'] = cols = []
        
        for index, column in enumerate(table.columns):
            cols.append({"id": column, "label": column, "type": column_types[index]})
        
        for row in table.data:
            row_list = [{"v": e} for e in row]
            rows.append({"c": row_list})
        return response

    def format(self, prev_results, query, table):
        # By default, every column is a string
        column_types = ['string'] * len(table.columns)

        # Identify column data types by looking at the first row only
        for row in table.data:
            for index, data in enumerate(row):
                if type(data) in [int, float]:
                    column_types[index] = 'number'
            break
        
        return self._generate_chart_data(table, column_types)