/***************************************************************************
 Module Name: 839P.H
 Purpose: the declaration of PCL839+ functions, data structures, status codes,
          constants, and messages
 Version: 3.01
 Date: 03/03/2004
 Copyright (c) 2004 Advantech Corp. Ltd.
 All rights reserved.
****************************************************************************/

#ifndef _INC_839P
#define _INC_839P


#ifdef _WIN31
	#define FLOAT   float
	#define CHAR    char
	#define USHORT  unsigned short
	#define SHORT   short
	#define ULONG   unsigned long
#endif


#ifdef __cplusplus
	extern "C"
	{
#endif

#define     PUBLIC   extern
#define     PRIVATE  static

/**************************************************************************
    Function Declaration
***************************************************************************/

#if !defined(_WIN31)
   #define FEXPORT __declspec (dllexport)
   #define FTYPE  CALLBACK
#else
   #define FEXPORT extern
   #define FTYPE  FAR PASCAL
#endif

// Function Declaration for PCL-839+
FEXPORT int FTYPE set_base(int address);
FEXPORT int FTYPE set_mode(int chan, int mode);
FEXPORT int FTYPE set_speed(int chan, int low_speed, int high_speed, int accelerate);
FEXPORT int FTYPE status(int chan);
FEXPORT int FTYPE m_stop(int chan);
FEXPORT int FTYPE slowdown(int chan);
FEXPORT int FTYPE sldn_stop(int chan);
FEXPORT int FTYPE waitrdy(int chan);
FEXPORT int FTYPE chkbusy(void);
FEXPORT int FTYPE out_port(int port_no, int value);
FEXPORT int FTYPE in_port(int port_no);
FEXPORT int FTYPE In_byte(int offset);
FEXPORT int FTYPE Out_byte(int offset , int value);
FEXPORT int FTYPE org(int chan, int dir1, int speed1, int dir2, int speed2 , int dir3, int speed3);
FEXPORT int FTYPE cmove(int chan, int dir1, int speed1, int dir2, int speed2, int dir3, int speed3);
FEXPORT int FTYPE pmove(int ch, int dir1, int speed1, long step1, int dir2, int speed2, long step2,
                        int dir3, int speed3, long step3);
//2003/4/18 \\\\\\\\\\\\\\\\\\\ 2.1 ///////////////////
FEXPORT int FTYPE arc(int plan_ch, int dirc, long x1, long y1, long x2, long y2);
FEXPORT int FTYPE line(int plan_ch, int dx, int dy);
FEXPORT int FTYPE line3D(int plan_ch, int dx, int dy, int dz);
//2003/4/18 /////////////////// 2.1 \\\\\\\\\\\\\\\\\\\/

#ifdef __cplusplus
}
#endif

#endif
