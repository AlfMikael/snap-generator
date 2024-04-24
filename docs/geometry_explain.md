## Calculations of point coordinates

md : Middle padding

t : Limb thickness 

wg : Width gap

r : Inner radius

w : width

wg : width gap

gb : gap buffer

ldg : ledge

fl : Flat length

lg : Length gap

alpha : Nose angle

nh : Nose height

mp : Middle padding

theta = arctan((P6y - P3y)/(P6x - P3x))
beta  = PI - theta

### P0 is the origin point
P0x = 0, P0y = 0

P1x = mp, P1y = 0

P2x = mp, P2y = gb - wg

P3x = mp, P3y = w/2 - wg - t

P4x = mp + r*(1-cos(beta), P4y = P2y + r*sin(beta)

P5x = mp + r, P5y = P2y

P6x = mmp + fl + lg,  P6y = P3y + t/2 

P7x = ?, P7y = ?

P8x = ?, P8y = ?

P9x = ?, P9y = ?

P10x = (mp + fl + gl) + nh*cos(alpha),  P10y = P11y + nh

P11x = mp + fl + gl, P11y = w/2 - wg

P12x = ldg , P12y = w/2 - wg

P13 = 0, P13y = (w)/2 + ldg 














