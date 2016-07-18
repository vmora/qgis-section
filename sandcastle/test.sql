create table well(
    id integer primary key
);
select AddGeometryColumn('well', 'geom', 2154, 'LINESTRING', 'XYZ'); 

insert into well(geom) values (GeomFromText('LINESTRING Z(0 0 0, 0 0 -10, 1 1 -20, 1 1 -30, 1 1 -40)', 2154));
insert into well(geom) values (GeomFromText('LINESTRING Z(10 0 0, 10 0 -10, 10 1 -20, 10 1 -30, 10 1 -40)', 2154));

