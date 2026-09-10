# Demo Data Systems: keys and joins

## Primary and foreign keys
A primary key uniquely identifies a row and cannot contain null values. A foreign key constrains references to a key in another table. A foreign key does not by itself make its column unique; many rows can reference the same parent.

## Practice tables
Teams(team_id, name): (10, Cedar), (20, Maple).
Members(member_id, name, team_id): (1, Ari, 10), (2, Bo, 10), (3, Cam, 20).
Joining Members to Teams on matching team_id produces three rows: Ari–Cedar, Bo–Cedar, Cam–Maple.

## Common misconception
Two members may share team_id 10 without violating the foreign key. member_id is the member identifier.
