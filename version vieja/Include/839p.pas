{/***************************************************************************		}
{ Module Name: 839P.pas																													}
{ Purpose: the declaration of PCL839+ functions, data structures, status codes,	}
{          constants, and messages																							}
{ Version: 3.01																																	}
{ Date: 11/03/2005																															}
{ Copyright (c) 2004 Advantech Corp. Ltd.																				}
{ All rights reserved.																													}
{****************************************************************************/	}
unit 839p;

const

type

Function set_base( Var address : Longint ): Longint; stdcall;
Function set_mode( Var chan : Longint; Var mode : Longint ): Longint; stdcall;
Function set_speed( Var chan : Longint; Var low_speed : Longint; Var high_speed : Longint; Var accelerate : Longint ): Longint; stdcall;
Function status( Var chan : Longint ): Longint; stdcall;
Function m_stop( Var chan : Longint ): Longint; stdcall;
Function slowdown( Var chan : Longint ): Longint; stdcall;
Function sldn_stop( Var chan : Longint ): Longint; stdcall;
Function waitrdy( Var chan : Longint ): Longint; stdcall;
Function chkbusy( ): Longint; stdcall;
Function out_port( Var port_no : Longint; Var value : Longint ): Longint; stdcall;
Function in_port( Var port_no : Longint ): Longint; stdcall;
Function In_byte( Var offset : Longint ): Longint; stdcall;
Function Out_byte( Var offset : Longint; Var value : Longint ): Longint; stdcall;
Function org( Var chan : Longint; Var dir1 : Longint; Var speed1 : Longint; Var dir2 : Longint; Var speed2 : Longint; Var dir3 : Longint; Var speed3 : Longint ): Longint; stdcall;
Function cmove( Var chan : Longint; Var dir1 : Longint; Var speed1 : Longint; Var dir2 : Longint; Var speed2 : Longint; Var dir3 : Longint; Var speed3 : Longint ): Longint; stdcall;
Function pmove( Var chan : Longint; Var dir1 : Longint; Var speed1 : Longint; Var step1 : Longint ; 
								Var dir2 : Longint; Var speed2 : Longint; Var step2 : Longint ; Var dir3 : Longint; Var speed3 : Longint; Var step3 : Longint  ): Longint; stdcall;

{\\\\\\\\\\\\\\\\\\\\\\\\\\\\\2.1\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\}
Function arc( Var plan_ch : Longint; Var dirc : Longint; Var x1 : Longint; Var y1 : Longint; Var x2 : Longint; Var y2 : Longint ): Longint; stdcall;
Function line( Var plan_ch : Longint; Var dx : Longint; Var dy : Longint ): Longint; stdcall;
Function line3D( Var plan_ch : Longint; Var dx : Longint; Var dy : Longint; Var dz : Longint ): Longint; stdcall;
{\\\\\\\\\\\\\\\\\\\\\\\\\\\\\2.1\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\}

implementation

{\\\\\\\\\\\\\\\\\\\\\Function implement declar\\\\\\\\\\\\\\\\\\\\\\\\\\\\\}
{\\\\\\\\\\Function implement declare \\\\\\\\\\\\\\\\\\
Function set_base; 				external 'Ads839p.dll';
Function set_mode;				external 'Ads839p.dll';
Function set_speed;				external 'Ads839p.dll';
Function status;					external 'Ads839p.dll';
Function m_stop;					external 'Ads839p.dll';
Function slowdown;				external 'Ads839p.dll';
Function sldn_stop;				external 'Ads839p.dll';
Function waitrdy;					external 'Ads839p.dll';
Function chkbusy;					external 'Ads839p.dll';
Function out_port;				external 'Ads839p.dll';
Function in_port;					external 'Ads839p.dll';
Function Out_byte;				external 'Ads839p.dll';
Function In_byte;					external 'Ads839p.dll';
Function org;							external 'Ads839p.dll';
Function cmove;						external 'Ads839p.dll';
Function pmove;						external 'Ads839p.dll';
Function arc;							external 'Ads839p.dll';
Function line;						external 'Ads839p.dll';
Function line3D;					external 'Ads839p.dll';

End.