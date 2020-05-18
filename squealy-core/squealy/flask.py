from squealy import Squealy
from .engines import Engine
from .loader import load_objects

class FlaskSquealy(Squealy):
    pass

class FlaskSqlAlchemyEngineFactory(EngineFactory):
    '''Yes, it does look like a Java/Spring developer wrote this class 

        This class assumes the following - 
        1) A Flask based application
        2) SQLAlchemy ORM
        3) Flask config object has SQLALCHEMY_DATABASE_URI defined, and is a valid database URI
        4) In case of multiple databases, SQLALCHEMY_BINDS is defined, and is a dictionary
    '''
    def get_engine(self, engine_name):
        from flask import current_app
        from sqlalchemy import create_engine

        if not engine_name or engine_name == 'default':
            if 'SQLALCHEMY_DATABASE_URI' in current_app.config:
                engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
            else:
                raise SquealyException("Cannot load engine 'default'. Missing configuration SQLALCHEMY_DATABASE_URI")
        else:
            binds = current_app.config.get('SQLALCHEMY_BINDS', {})
            if engine_name in binds:
                conn_url = binds[engine_name]
                engine = create_engine(conn_url)
            else:
                raise raise SquealyException("Cannot load engine '" + engine_name + ', did you configure SQLALCHEMY_BINDS?")
        
        if not engine:
            raise SquealyException("Did not expect engine to be null at this point")

        return SqlAlchemyEngine(engine)


class SqlAlchemyEngine(Engine):
    def __init__(self, engine):
        self.engine = engine
    
    def execute(self, query, bind_params):
        with self.engine.connect() as conn:
            result = conn.execute(finalquery, bindparams)
            cols = result.keys()
            rows = result.fetchall()
        table = Table(columns=result.keys(), data=[r.values() for r in rows])

    def execute_for_json(self, query, bind_params):
        with self.engine.connect() as conn:
            result = conn.execute(finalquery, bindparams)
            return result.fetchone()[0]
