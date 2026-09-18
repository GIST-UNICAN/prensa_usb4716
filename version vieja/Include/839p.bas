Attribute VB_Name = "Module"
'**************************************************************************
'    Function Declaration for PCL-839
'**************************************************************************
Declare Function set_base Lib "ads839p.dll" (ByVal address As Long) As Long
Declare Function set_mode Lib "ads839p.dll" (ByVal chan As Long, ByVal mode As Long) As Long
Declare Function set_speed Lib "ads839p.dll" (ByVal chan As Long, ByVal low_speed As Long, ByVal high_speed As Long, ByVal accelerate As Long) As Long
Declare Function status Lib "ads839p.dll" (ByVal chan As Long) As Long
Declare Function m_stop Lib "ads839p.dll" (ByVal chan As Long) As Long
Declare Function slowdown Lib "ads839p.dll" (ByVal chan As Long) As Long
Declare Function sldn_stop Lib "ads839p.dll" (ByVal chan As Long) As Long
Declare Function waitrdy Lib "ads839p.dll" (ByVal chan As Long) As Long
Declare Function chkbusy Lib "ads839p.dll" () As Long
Declare Function out_port Lib "ads839p.dll" (ByVal port_no As Long, ByVal value As Long) As Long
Declare Function in_port Lib "ads839p.dll" (ByVal port_no As Long) As Long
Declare Function In_byte Lib "ads839p.dll" (ByVal offset As Long) As Long
Declare Function Out_byte Lib "ads839p.dll" (ByVal offset As Long, ByVal value As Long) As Long
Declare Function org Lib "ads839p.dll" (ByVal chan As Long, ByVal dir1 As Long, ByVal speed1 As Long, ByVal dir2 As Long, ByVal speed2 As Long, ByVal dir3 As Long, ByVal speed3 As Long) As Long
Declare Function cmove Lib "ads839p.dll" (ByVal chan As Long, ByVal dir1 As Long, ByVal speed1 As Long, ByVal dir2 As Long, ByVal speed2 As Long, ByVal dir3 As Long, ByVal speed3 As Long) As Long
Declare Function pmove Lib "ads839p.dll" (ByVal chan As Long, ByVal dir1 As Long, ByVal speed1 As Long, ByVal step1 As Long, ByVal dir2 As Long, ByVal speed2 As Long, ByVal step2 As Long, ByVal dir3 As Long, ByVal speed3 As Long, ByVal step3 As Long) As Long
Declare Function line Lib "ads839p.dll" (ByVal plan_ch As Long, ByVal dx As Long, ByVal dy As Long) As Long
Declare Function line3D Lib "ads839p.dll" (ByVal plan_ch As Long, ByVal dx As Long, ByVal dy As Long, ByVal dz As Long) As Long
Declare Function arc Lib "ads839p.dll" (ByVal plan_ch As Long, ByVal dirc As Long, ByVal x1 As Long, ByVal y1 As Long, ByVal x2 As Long, ByVal y2 As Long) As Long


