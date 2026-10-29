import duckdb
import pytest

@pytest.fixture
def db():
    c=duckdb.connect()
    c.execute('create table courses(code_module varchar,code_presentation varchar,module_presentation_length int)')
    c.execute("insert into courses values ('AAA','2013J',100)")
    c.execute('create table studentRegistration(code_module varchar,code_presentation varchar,id_student int,date_registration int,date_unregistration int)')
    c.execute("insert into studentRegistration values ('AAA','2013J',1,-3,null),('AAA','2013J',2,0,8),('AAA','2013J',3,null,null),('AAA','2013J',4,-2,-1),('AAA','2013J',5,1,null),('AAA','2013J',6,-1,null)")
    c.execute('create table vle(id_site int,code_module varchar,code_presentation varchar,activity_type varchar,week_from int,week_to int)')
    c.execute("insert into vle values(10,'AAA','2013J','oucontent',null,null),(11,'AAA','2013J','homepage',null,null)")
    c.execute('create table studentVle(code_module varchar,code_presentation varchar,id_student int,id_site int,date int,sum_click int)')
    # id1: W1 days 0,6; W2 day7,13. duplicate day0 changes clicks but not days.
    # id2: W1 day0; W2 day9 after withdrawal => retained by base, strict removes.
    # id6: zero clicks, negative days, day14 cannot qualify as W1/W2.
    c.execute("""insert into studentVle values
    ('AAA','2013J',1,10,-1,4),('AAA','2013J',1,10,0,5),('AAA','2013J',1,10,0,5),
    ('AAA','2013J',1,11,6,2),('AAA','2013J',1,10,7,1),('AAA','2013J',1,10,13,1),
    ('AAA','2013J',2,11,0,1),('AAA','2013J',2,10,9,1),
    ('AAA','2013J',6,10,0,0),('AAA','2013J',6,10,-1,2),('AAA','2013J',6,10,14,1),
    ('AAA','2013J',6,999,0,9),('AAA','2013J',999,10,0,1),
    ('AAA','2013J',null,10,0,1),('AAA','2013J',1,10,101,1)
    """)
    yield c
    c.close()
