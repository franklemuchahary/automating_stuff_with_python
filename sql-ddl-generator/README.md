# SQL DDL Query Generator

This jupyter notebook helps in converting google sheet tables into DDL queries for PostgreSQL, SQL Server, or MySQL. It is mainly helpful for working with smaller datasets when we want to create a sample dataset and work on a building the query logic. It is also helpful during interviews whether you are interviewing someone or getting interviewed. A sample dataset can be quickly created in a google sheet and the DDL query can be copy-pasted into tools like [SQLFiddle](http://sqlfiddle.com/), [DBFiddle](https://dbfiddle.uk/) for working on the analytical query.

<br><br>
*How to Use:*
- Create a google sheet.
- Convert it into open view access for everyone.
- Copy the google sheet link (Example: https://docs.google.com/spreadsheets/d/1u9xez7cCm2zTK65cn1WrtmKDK2FuqfckQ44PxGXfmLc/edit#gid=0) and set the varibale `GOOGLE_SHEET_LINK` to this value.
- Run the code.

<br><br>
*Sample Input Table:*
<pre>
  fse_id fse_name  state   city  fse_score
0   fse1     fse1  Delhi  Delhi        1.0
1   fse2     fse2  Delhi  Delhi        2.0
2   fse3     fse3  Delhi  Delhi        3.0
</pre>

*Sample Output:*

<pre>
    create table table2 (
    	fse_id varchar(255),
        fse_name varchar(255),
        state varchar(255),
        city varchar(255),
        fse_score float
    );
    
    insert into 
        table2 (fse_id, fse_name, state, city, fse_score) 
    values
        ('fse1', 'fse1', 'Delhi', 'Delhi', '1.0'),
        ('fse2', 'fse2', 'Delhi', 'Delhi', '2.0'),
        ('fse3', 'fse3', 'Delhi', 'Delhi', '3.0'),
        ('fse4', 'fse4', 'MH', 'Bombay', '10.0'),
        ('fse5', 'fse5', 'MH', 'Nagpur', '15.0')
    ;
    
    select * from table2;
</pre>
