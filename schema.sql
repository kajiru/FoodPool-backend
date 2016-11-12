drop table if exists Pools;
drop table if exists Orders;
create table Pools (
    restaurant varchar(30), --  “In n Out”,
    return_time datetime, --   1478939164,
    num_orders integer, --  5
    pickup_location varchar(40), --  “Room 383”\
    has_arrived boolean
);

create table Orders (
    name varchar(40), --  “Adrien Truong”
    food_order varchar(40), -- “1 cheeseburger with fries”
    total integer, -- 700 // in cents, so this is $7
    phone varchar(30) -- “7143885687”
);
