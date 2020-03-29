

def load_charts(base_dir):
    data = {}
    for elem in Path(base_dir).rglob("*\.ya?ml"):
        with open(ymlfile) as f:
            objects = yaml.safe_load_all(f)
            for rawobj in objects:
                kind = rawobj['kind']
                if kind !== 'chart':
                    raise Exception(f"Unknown object of kind = {kind} in {ymlfile}")
                obj = Chart(**rawchart)
                data[rawobj['kind']].append(obj)
        
    return data



