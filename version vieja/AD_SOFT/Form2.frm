VERSION 5.00
Begin VB.Form Form2 
   Caption         =   "Form2"
   ClientHeight    =   2400
   ClientLeft      =   48
   ClientTop       =   432
   ClientWidth     =   3744
   LinkTopic       =   "Form2"
   ScaleHeight     =   2400
   ScaleWidth      =   3744
   StartUpPosition =   3  'Windows Default
   Begin VB.CommandButton Command2 
      Caption         =   "Command2"
      Height          =   492
      Left            =   2040
      TabIndex        =   2
      Top             =   1080
      Width           =   1092
   End
   Begin VB.CommandButton Command1 
      Caption         =   "SI"
      Height          =   492
      Left            =   480
      TabIndex        =   1
      Top             =   1080
      Width           =   972
   End
   Begin VB.Label Label1 
      Caption         =   "¿DESEA SALIR SIN GUARDAR LOS REGISTRADOS?"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H000000FF&
      Height          =   852
      Left            =   360
      TabIndex        =   0
      Top             =   240
      Width           =   3252
   End
End
Attribute VB_Name = "Form2"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
