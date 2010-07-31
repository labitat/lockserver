create table hashes (id integer primary key autoincrement, hash varchar(40), accesstype integer, charges integer, member varchar(60), expires date, lastuse date);
create table log (id integer primary key autoincrement, event integer, eventtime datetime, hash integer);
