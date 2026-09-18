VERSION 5.00
Begin VB.Form frmDevSel 
   Appearance      =   0  'Flat
   BackColor       =   &H00FFFFFF&
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "Analog Input Demo: Select Input Device"
   ClientHeight    =   7716
   ClientLeft      =   2196
   ClientTop       =   2160
   ClientWidth     =   11496
   BeginProperty Font 
      Name            =   "MS Sans Serif"
      Size            =   7.8
      Charset         =   0
      Weight          =   700
      Underline       =   0   'False
      Italic          =   0   'False
      Strikethrough   =   0   'False
   EndProperty
   ForeColor       =   &H000000FF&
   LinkTopic       =   "Form1"
   PaletteMode     =   1  'UseZOrder
   ScaleHeight     =   7716
   ScaleWidth      =   11496
   Begin VB.CommandButton DBUJAR 
      Caption         =   "DIBUJAR"
      Height          =   612
      Left            =   5280
      TabIndex        =   34
      Top             =   6360
      Width           =   3012
   End
   Begin VB.CommandButton RESET 
      Caption         =   "RESET"
      Enabled         =   0   'False
      Height          =   492
      Left            =   6720
      TabIndex        =   33
      Top             =   840
      Width           =   1335
   End
   Begin VB.CommandButton guardar 
      Caption         =   "Guardar datos"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   612
      Left            =   480
      TabIndex        =   32
      Top             =   5880
      Width           =   3132
   End
   Begin VB.CommandButton iniciar 
      Caption         =   "Iniciar Lecturas"
      Height          =   492
      Left            =   2760
      TabIndex        =   31
      Top             =   840
      Width           =   1335
   End
   Begin VB.CommandButton parar 
      Caption         =   "Parar Lecturas"
      Enabled         =   0   'False
      Height          =   492
      Left            =   4560
      TabIndex        =   30
      Top             =   840
      Width           =   1335
   End
   Begin VB.TextBox Text2 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   13.8
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   348
      Left            =   600
      Locked          =   -1  'True
      TabIndex        =   29
      Text            =   "50"
      Top             =   3000
      Width           =   1092
   End
   Begin VB.TextBox Text1 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BackColor       =   &H00FFFFFF&
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   13.8
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   348
      Left            =   4440
      Locked          =   -1  'True
      TabIndex        =   27
      Text            =   "00.000"
      Top             =   3000
      Width           =   1332
   End
   Begin VB.TextBox REFERENCIA 
      Height          =   288
      Left            =   3720
      TabIndex        =   23
      Text            =   "1"
      Top             =   4680
      Width           =   1332
   End
   Begin VB.TextBox FICHERODATOS 
      Height          =   372
      Left            =   480
      TabIndex        =   21
      Text            =   " "
      Top             =   4080
      Width           =   4572
   End
   Begin VB.DirListBox carpeta 
      Height          =   2232
      Left            =   5280
      TabIndex        =   19
      Top             =   3840
      Width           =   5892
   End
   Begin VB.DriveListBox disco 
      Height          =   288
      Left            =   7200
      TabIndex        =   18
      Top             =   3120
      Width           =   3852
   End
   Begin VB.TextBox DEFORMACION_MAXIMA 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BackColor       =   &H00FFFFFF&
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   13.8
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   348
      Left            =   4440
      Locked          =   -1  'True
      TabIndex        =   16
      Text            =   "00.000"
      Top             =   2520
      Width           =   1332
   End
   Begin VB.TextBox CARGA_MAXIMA 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   13.8
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   348
      Left            =   600
      Locked          =   -1  'True
      TabIndex        =   14
      Text            =   "0000"
      Top             =   2520
      Width           =   1092
   End
   Begin VB.CommandButton tara_canal 
      Caption         =   "TARAR"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   600
      TabIndex        =   6
      Top             =   960
      Width           =   1452
   End
   Begin VB.TextBox lectotal 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   10.2
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   312
      Left            =   6360
      Locked          =   -1  'True
      TabIndex        =   5
      Text            =   "0"
      Top             =   120
      Width           =   1452
   End
   Begin VB.Timer Timer1 
      Interval        =   1
      Left            =   7920
      Top             =   240
   End
   Begin VB.TextBox deformacion 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BackColor       =   &H00FFFFFF&
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   16.2
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   492
      Left            =   4440
      Locked          =   -1  'True
      TabIndex        =   4
      Text            =   "00.000"
      Top             =   1872
      Width           =   1332
   End
   Begin VB.TextBox carga 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   16.2
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H00000000&
      Height          =   468
      Left            =   600
      Locked          =   -1  'True
      TabIndex        =   3
      Text            =   "0000"
      Top             =   1872
      Width           =   1092
   End
   Begin VB.CommandButton cmdExit 
      BackColor       =   &H80000005&
      Caption         =   "Salir"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   13.8
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   7440
      MaskColor       =   &H00000000&
      TabIndex        =   1
      Top             =   7080
      Width           =   1095
   End
   Begin VB.ListBox lstDevice 
      Appearance      =   0  'Flat
      Height          =   216
      Left            =   2880
      TabIndex        =   0
      Top             =   120
      Width           =   1932
   End
   Begin VB.Label Label11 
      BackColor       =   &H80000009&
      BackStyle       =   0  'Transparent
      Caption         =   "mm"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   6000
      TabIndex        =   28
      Top             =   3000
      Width           =   612
   End
   Begin VB.Label Label10 
      Alignment       =   1  'Right Justify
      BackColor       =   &H80000009&
      Caption         =   "Kp"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   1680
      TabIndex        =   26
      Top             =   3000
      Width           =   492
   End
   Begin VB.Label FICHEROSALIDA 
      BackColor       =   &H80000010&
      Height          =   372
      Left            =   480
      TabIndex        =   25
      Top             =   5400
      Width           =   3132
   End
   Begin VB.Label Label1 
      Alignment       =   1  'Right Justify
      AutoSize        =   -1  'True
      Caption         =   "Fichero de Salida"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H8000000D&
      Height          =   240
      Index           =   6
      Left            =   480
      TabIndex        =   24
      Top             =   5160
      Width           =   1752
   End
   Begin VB.Label Label1 
      Alignment       =   1  'Right Justify
      AutoSize        =   -1  'True
      BackColor       =   &H8000000B&
      Caption         =   "REFERENCIA DE PROBETA"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H8000000D&
      Height          =   240
      Index           =   4
      Left            =   480
      TabIndex        =   22
      Top             =   4680
      Width           =   2880
   End
   Begin VB.Label Label1 
      Alignment       =   1  'Right Justify
      AutoSize        =   -1  'True
      Caption         =   "NOMBRE DE FICHERO"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H8000000D&
      Height          =   240
      Index           =   5
      Left            =   480
      TabIndex        =   20
      Top             =   3720
      Width           =   2388
   End
   Begin VB.Label Label9 
      BackColor       =   &H80000009&
      BackStyle       =   0  'Transparent
      Caption         =   "mm"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   6000
      TabIndex        =   17
      Top             =   2520
      Width           =   612
   End
   Begin VB.Label Label8 
      BackColor       =   &H80000009&
      BackStyle       =   0  'Transparent
      Caption         =   "Kp"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   1920
      TabIndex        =   15
      Top             =   2520
      Width           =   492
   End
   Begin VB.Label Label7 
      Alignment       =   1  'Right Justify
      BackColor       =   &H80000009&
      Caption         =   "MAXIMA"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   252
      Left            =   2880
      TabIndex        =   13
      Top             =   2520
      Width           =   1092
   End
   Begin VB.Label Label6 
      Alignment       =   1  'Right Justify
      BackColor       =   &H80000009&
      Caption         =   "ACTUAL"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   252
      Left            =   2880
      TabIndex        =   12
      Top             =   1920
      Width           =   1092
   End
   Begin VB.Label Label5 
      Alignment       =   1  'Right Justify
      BackColor       =   &H80000009&
      Caption         =   "DEFORMACION"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   252
      Left            =   4320
      TabIndex        =   11
      Top             =   1560
      Width           =   2052
   End
   Begin VB.Label Label4 
      Alignment       =   1  'Right Justify
      BackColor       =   &H80000009&
      Caption         =   "CARGAS"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   252
      Left            =   600
      TabIndex        =   10
      Top             =   1560
      Width           =   1092
   End
   Begin VB.Label Label3 
      Alignment       =   1  'Right Justify
      BackColor       =   &H80000009&
      Caption         =   "Lecturas"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   252
      Left            =   5280
      TabIndex        =   9
      Top             =   120
      Width           =   972
   End
   Begin VB.Label Label2 
      BackColor       =   &H80000009&
      BackStyle       =   0  'Transparent
      Caption         =   "Kp"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Left            =   1920
      TabIndex        =   8
      Top             =   1920
      Width           =   492
   End
   Begin VB.Label Label1 
      BackColor       =   &H80000009&
      BackStyle       =   0  'Transparent
      Caption         =   "mm"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   372
      Index           =   0
      Left            =   6000
      TabIndex        =   7
      Top             =   1920
      Width           =   612
   End
   Begin VB.Label labDevLst 
      Appearance      =   0  'Flat
      BackColor       =   &H80000005&
      Caption         =   " TARJETA ENCONTRADA:"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H80000008&
      Height          =   252
      Left            =   120
      TabIndex        =   2
      Top             =   120
      Width           =   3372
   End
End
Attribute VB_Name = "frmDevSel"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Dim lpDEVCONFIG_AI As DEVCONFIG_AI
Dim lpAIGetConfig As PT_AIGetConfig
Dim gnNumOfSubdevices As Integer
Dim bRun As Boolean
Dim voltage As Single
Dim canal(1, 1000) As Single
Dim contador_lecturas As Long
Dim numero_lecturas As Long
Dim taracanal0, taracanal1, corrige0, corrige1 As Single
Dim Constante_carga, Constante_deformacion As Single
Dim inicio_tarado As String
Dim valor_carga, valor_deformacion As Single
Dim CARGA_MAX, DEFORMACION_MAX, deformacion_50 As Integer
Dim carmedia, defmedia As Single
Dim lecturas As Integer
Dim ALMACEN, MIRUTA, RUTAALMACEN As String
Dim salidadatos, guardarlecturas As String
Dim directorio As String




Function TestStr(DStr As String, TStr As String) As Boolean
  Dim lenD, lenT As Integer
  Dim I As Integer

  TestStr = False
  lenD = Len(DStr)
  lenT = Len(TStr)

  For I = 1 To (lenD - lenT + 1)
    If (Mid(DStr, I, lenT) = TStr) Then
      TestStr = True
    End If
  Next I

  If DStr = "" Then
    TestStr = True
  End If
End Function

Private Sub carpeta_Change()
directorio = carpeta.Path
caracterfinal = Mid$(directorio, Len(directorio), 1)
If caracterfinal <> "\" Then directorio = directorio + "\"
FICHEROSALIDA = directorio + FICHERODATOS + "-" + REFERENCIA
End Sub

Private Sub cmdExit_Click()
  If bRun Then
    ErrCde = DRV_DeviceClose(DeviceHandle)
    If (ErrCde <> 0) Then
      DRV_GetErrorMessage ErrCde, szErrMsg
      Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
    End If
  End If
  End
End Sub

Private Sub UpDatecarga(fValue As Single)

    ' Since the output box is too small to display all the digits
    ' of the input voltage, so it must use to format to get better
    ' display.
    carga.Text = Format(fValue, "###0.000")
End Sub
Private Sub UpDatedeformacion(fValue As Single)

    ' Since the output box is too small to display all the digits
    ' of the input voltage, so it must use to format to get better
    ' display.
    deformacion.Text = Format(fValue, "###0.000")
End Sub

Private Sub DIBUJAR_Click()
RetVal = Shell("C:\Archivos de programa\Microsoft Office\Office10\EXCEL.EXE C:\MARSHALL2007\AD_SOFT\dibuja_datos.xls", 1)
End Sub

Private Sub DBUJAR_Click()
frmDevSel.Visible = False
 FILTRAR.Visible = True
End Sub

Private Sub disco_Change()
  On Error GoTo salta
    Dim respuesta As Integer
    carpeta.Path = disco.Drive
    Exit Sub
salta:
    respuesta = MsgBox(Err.Description, 5, "No hay disco")
    If respuesta = 4 Then Resume
End Sub

Private Sub FICHERODATOS_Change()
FICHEROSALIDA = directorio + FICHERODATOS + "-" + REFERENCIA
End Sub

Private Sub FICHEROSALIDA_Click()
Text.FICHEROSALIDA_Click() = FICHEROSALIDA
End Sub

Private Sub Form_Load()
  Dim gnNumOfDevices As Integer
  Dim nOutEntries As Integer
  Dim I, ii As Integer
  Dim tt As Long
  Dim tempStr As String
    
  bRun = False
    'constante de deformacion 1 V = 2.643095 mm
    'constante de deformacion 1 V = -1970.57 mm
    Constante_deformacion = 2.643095
    Constante_carga = -1970.57
    contador_lecturas = 0
    inicio_tarado = "no"
    numero_lecturas = 10
    
  ' Add type of PC Laboratory Card
  tt = DRV_GetAddress(devicelist(0))
  ErrCde = DRV_DeviceGetList(tt, MaxEntries, nOutEntries)
  If (ErrCde <> 0) Then
    DRV_GetErrorMessage ErrCde, szErrMsg
    Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
    Exit Sub
  End If

  ' Return the number of devices which you install in the system using
  ' Device Installation
  ErrCde = DRV_DeviceGetNumOfList(gnNumOfDevices)
  If (ErrCde <> 0) Then
    DRV_GetErrorMessage ErrCde, szErrMsg
    Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
    Exit Sub
  End If

  For I = 0 To (gnNumOfDevices - 1)
    tempStr = ""
    For ii = 0 To MaxDevNameLen
      tempStr = tempStr + Chr(devicelist(I).szDeviceName(ii))
    Next ii
      lstDevice.AddItem tempStr
  Next I

'     labChannel.Enabled = False
'     lstChannel.Enabled = False
'     labVoltageRange.Enabled = False
'     lstVoltageRange.Enabled = False
    'labExpChl.enabled = False
    'lstExpChl.enabled = False
    'labThermocouple.enabled = False
    'lstThermocouple.enabled = False
    'cmdRun.Enabled = True
    
End Sub


Private Sub guardar_Click()
Open RUTAALMACEN For Input As 5
Open FICHEROSALIDA + ".txt" For Output As 6

While Not EOF(5)
    Line Input #5, A$
    Print #6, A$
Wend
Close

End Sub

Private Sub Iniciar_Click()
        parar.Enabled = True
        iniciar.Enabled = False
        tara_canal.Enabled = False
        guardarlecturas = "si"
        Close
        ALMACEN = "salidadatos.txt"
        Open ALMACEN For Output As #5
        MIRUTA = CurDir
        RUTAALMACEN = MIRUTA + "\" + "salidadatos.txt"
End Sub

Private Sub lstDevice_Click()
  Dim I, ii As Integer
  Dim tempNum As Integer
  Dim TestRes As Boolean

  Dim nOutEntries As Integer
  Dim lpSubDeviceList As Long
  Dim dwDeviceNum As Long
'  Dim lpDEVCONFIG_AI As DEVCONFIG_AI
  
  Dim iMaxSingleChannel As Integer
  Dim iMaxDiffChannel As Integer
  
  

'   lstChannel.Clear
'   lstVoltageRange.Clear
  'lstExpChl.Clear

  ' Avoid to open Advantech Demo Card
  TestRes = TestStr(lstDevice.Text, "DEMO")
  If (TestRes) Then
    labModule.Enabled = False
    lstModule.Enabled = False
    labChannel.Enabled = False
    lstChannel.Enabled = False
    labVoltageRange.Enabled = False
    lstVoltageRange.Enabled = False
    'labExpChl.enabled = False
    'lstExpChl.enabled = False
    'labThermocouple.enabled = False
    'lstThermocouple.enabled = False
    lstChannel.AddItem "No Use"
    cmdRun.Enabled = False
  End If

  If (Not TestRes) Then
  ' Check if there is any device attatched on this COM port or CAN
    gnNumOfSubdevices = devicelist(lstDevice.ListIndex).nNumOfSubdevices
    If (gnNumOfSubdevices > MaxDev) Then
      gnNumOfSubdevices = MaxDev
    End If

    ' retrieve the information of all installed devices
    If (gnNumOfSubdevices <> 0) Then
      dwDeviceNum = devicelist(lstDevice.ListIndex).dwDeviceNum
      lpSubDeviceList = DRV_GetAddress(SubDevicelist(0))
      ErrCde = DRV_DeviceGetSubList(dwDeviceNum, lpSubDeviceList, gnNumOfSubdevices, nOutEntries)
      If (ErrCde <> 0) Then
        DRV_GetErrorMessage ErrCde, szErrMsg
        Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
        Exit Sub
      End If
      For I = 0 To (gnNumOfSubdevices - 1)
        tempStr = ""
        For ii = 0 To MaxDevNameLen
            tempStr = tempStr + Chr(SubDevicelist(I).szDeviceName(ii))
        Next ii
        lstModule.AddItem tempStr
      Next I
      lstModule.Enabled = True
      labModule.Enabled = True
   End If

   ' Data Acquisition & Control or Digital I/O card
   If (gnNumOfSubdevices = 0) Then
     dwDeviceNum = devicelist(lstDevice.ListIndex).dwDeviceNum
      ErrCde = DRV_DeviceOpen(dwDeviceNum, DeviceHandle)
      If (ErrCde <> 0) Then
        DRV_GetErrorMessage ErrCde, szErrMsg
        Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
        Exit Sub
      Else
        bRun = True
      End If

      ptDevGetFeatures.buffer = DRV_GetAddress(lpDevFeatures)
      ErrCde = DRV_DeviceGetFeatures(DeviceHandle, ptDevGetFeatures)
      If (ErrCde <> 0) Then
        DRV_GetErrorMessage ErrCde, szErrMsg
        Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
        Exit Sub
      End If

      ptAIGetConfig.buffer = DRV_GetAddress(lpDEVCONFIG_AI)
      ErrCde = DRV_AIGetConfig(DeviceHandle, ptAIGetConfig)
      If (ErrCde <> 0) Then
        DRV_GetErrorMessage ErrCde, szErrMsg
        Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
        Exit Sub
      End If
     AiCtrMode = lpDEVCONFIG_AI.usGainCtrMode
     Dim BoardID As Integer
     BoardID = lpDEVCONFIG_AI.dwBoardID
     
      'get the max channel number
      'tempNum = lpDevFeatures.usMaxAISiglChl
      iMaxSingleChannel = lpDevFeatures.usMaxAISiglChl
      iMaxDiffChannel = lpDevFeatures.usMaxAIDiffChl
      
      If iMaxSingleChannel > iMaxDiffChannel Then
         tempNum = iMaxSingleChannel
      Else
         tempNum = iMaxDiffChannel
      End If
      
      If (tempNum > 0) Then
        For I = 0 To (tempNum - 1)
          temp$ = "Chan#" + Str(I)
'           lstChannel.AddItem temp$, i
        Next I
'         lstChannel.Text = lstChannel.List(0)
'         labChannel.Enabled = True
'         lstChannel.Enabled = True
      End If

      ' add gain code list
      tempNum = lpDevFeatures.usNumGain
      If (lpDevFeatures.usNumGain > 0) Then
        For I = 0 To (lpDevFeatures.usNumGain - 1)
          tempStr = ""
          For ii = 0 To 15
              tempStr = tempStr + Chr(lpDevFeatures.glGainList(I).szGainStr(ii))
          Next ii
'           lstVoltageRange.AddItem tempStr
        Next I
'         lstVoltageRange.Text = lstVoltageRange.List(0)
'         lstVoltageRange.Enabled = True
'         labVoltageRange.Enabled = True
      End If

      'cmdRun.Enabled = True
    End If
  End If
End Sub


Private Sub lstModule_Click()
    Dim I, ii As Integer
    Dim dwDeviceNum As Long
    Dim tempNum As Integer

    lstChannel.Clear
    lstVoltageRange.Clear
    ' open COM device or CAN device
    dwDeviceNum = SubDevicelist(lstModule.ListIndex).dwDeviceNum
    ErrCde = DRV_DeviceOpen(dwDeviceNum, DeviceHandle)
    If (ErrCde <> 0) Then
       DRV_GetErrorMessage ErrCde, szErrMsg
       Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
       Exit Sub
    Else
       bRun = True
    End If

    ptDevGetFeatures.buffer = DRV_GetAddress(lpDevFeatures)
    ErrCde = DRV_DeviceGetFeatures(DeviceHandle, ptDevGetFeatures)
    If (ErrCde <> 0) Then
       DRV_GetErrorMessage ErrCde, szErrMsg
       Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
       Exit Sub
    End If

    ' Add analog input channel item
      ptAIGetConfig.buffer = DRV_GetAddress(lpDEVCONFIG_AI)
      ErrCde = DRV_AIGetConfig(DeviceHandle, ptAIGetConfig)
      If (ErrCde <> 0) Then
        DRV_GetErrorMessage ErrCde, szErrMsg
        Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
        Exit Sub
      End If

        tempNum = lpDevFeatures.usMaxAISiglChl
      If (tempNum > 0) Then
        For I = 0 To (tempNum - 1)
          temp$ = "Chan#" + Str(I)
          lstChannel.AddItem temp$, I
        Next I
        lstChannel.Text = lstChannel.List(0)
        labChannel.Enabled = True
        lstChannel.Enabled = True
      End If

      ' add gain code list
      tempNum = lpDevFeatures.usNumGain
      If (lpDevFeatures.usNumGain > 0) Then
        For I = 0 To (lpDevFeatures.usNumGain - 1)
          tempStr = ""
          For ii = 0 To 15
              tempStr = tempStr + Chr(lpDevFeatures.glGainList(I).szGainStr(ii))
          Next ii
          lstVoltageRange.AddItem tempStr
        Next I
        lstVoltageRange.Text = lstVoltageRange.List(0)
        lstVoltageRange.Enabled = True
        labVoltageRange.Enabled = True
      End If
'******************************************************************
        
        
    tarar.Enabled = True
    iniciar.Enabled = True
    parar.Enabled = False
    Reset.Enabled = False
    Timer1.Enabled = True
        
        
        
     
        
        
'******************************************************************
      cmdRun.Enabled = True
End Sub


Private Sub parar_Click()
    tara_canal.Enabled = False
    iniciar.Enabled = False
    parar.Enabled = False
    Reset.Enabled = True
    Timer1.Enabled = False
   Close
    guardarlecturas = "no"
End Sub

Private Sub REFERENCIA_Change()
FICHEROSALIDA = directorio + "\" + FICHERODATOS + "-" + REFERENCIA
End Sub

Private Sub RESET_Click()
    tara_canal.Enabled = True
    iniciar.Enabled = True
    parar.Enabled = False
    Reset.Enabled = False
    Timer1.Enabled = True
       
End Sub

Private Sub Timer1_Timer()
Dim tempNum As Integer
lstDevice = "PCL-816 I/O=200H"
lstChannel = "Chan# 0"
lstVoltageRange = "+/-5V"

'   tempNum = lstVoltageRange.ListIndex
 '  AiCtrMode = lpDEVCONFIG_AI.usGainCtrMode
 '  lpAIConfig.DasChan = lstChannel.ListIndex

tempNum = 1
AiCtrMode = 1
contador_lecturas = contador_lecturas + 1

'------------------------leo canal 0--------------------
'lpAIConfig.DasChan es el numero del canal
                    lpAIConfig.DasChan = 0

  ' Gain code no use for ADAM series
  If gnNumOfSubdevices = 0 Then
        lpAIConfig.DasGain = lpDevFeatures.glGainList(tempNum).usGainCde
  End If
  ErrCde = DRV_AIConfig(DeviceHandle, lpAIConfig)
                    dcanal0 = DeviceHandle
  If (ErrCde <> 0) Then
    DRV_GetErrorMessage ErrCde, szErrMsg
    Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
    Exit Sub
  End If

  lectura

'------------------------leo canal 1--------------------
'lpAIConfig.DasChan es el numero del canal
                    lpAIConfig.DasChan = 1

  ' Gain code no use for ADAM series
  If gnNumOfSubdevices = 0 Then
        lpAIConfig.DasGain = lpDevFeatures.glGainList(tempNum).usGainCde
  End If
  ErrCde = DRV_AIConfig(DeviceHandle, lpAIConfig)
                dcanal1 = DeviceHandle
  If (ErrCde <> 0) Then
    DRV_GetErrorMessage ErrCde, szErrMsg
    Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
    Exit Sub
  End If
  lectura
'---------------------salida de datos-------------------
If guardarlecturas = "si" Then
        defmedia = defmedia + valor_deformacion
        carmedia = carmedia + valor_carga
        lecturas = lecturas + 1
        If lecturas > 9 Then
            defmedia = Int(100 * defmedia / lecturas)
           carmedia = Int(carmedia / lecturas)
             Print #5, defmedia, " * ", carmedia, " * ", Timer
             lecturas = 0
             carmedia = 0
             defmedia = 0
        End If
             
End If
'-------------------------------------------

End Sub
Private Sub lectura()
 'numero de puntos para la media
  'El numero de lecturas por segundo se obtiene dividiendo
  '1000 entre tmrRead
'tmrRead.Interval = 10
  'shapLed.FillColor = QBColor(12)
  'lpAIConfig.DasChan = 0
  
  
  AiVolIn.chan = lpAIConfig.DasChan
  AiVolIn.gain = lpAIConfig.DasGain
  'AiVolIn.chan = 0
  'AiVolIn.TrigMode = AiCtrMode
  'internal triger
    AiVolIn.TrigMode = 0
  AiVolIn.voltage = DRV_GetAddress(voltage)
  ErrCde = DRV_AIVoltageIn(DeviceHandle, AiVolIn)
  If (ErrCde <> 0) Then
    DRV_GetErrorMessage ErrCde, szErrMsg
    Response = MsgBox(szErrMsg, vbOKOnly, "Error!!")
    Exit Sub
  End If
'----------------------------------------------
If AiVolIn.chan = 0 Then
        canal(0, contador_lecturas) = voltage
        
        '+++++++++++++++++++++++++++++++++++++++++++++
        If contador_lecturas = numero_lecturas Then
            canal(0, 0) = 0
            '
            For I = 1 To numero_lecturas
                canal(0, 0) = canal(0, 0) + canal(0, I)
            Next I
            
            canal(0, 0) = canal(0, 0) / numero_lecturas
            valor_carga = (canal(0, 0) - corrige0) * Constante_carga
            taracanal0 = canal(0, 0)
            
            '*********************************************
            If voltage < -4.95 Or voltage > 4.95 Then
                carga.BackColor = &H8080FF
            Else
                carga.BackColor = &H80000005
            End If
            '*********************************************
            carga.Text = Format(valor_carga, "#####")
            '*********************************************
            If valor_carga > CARGA_MAX Then
                CARGA_MAX = valor_carga
                CARGA_MAXIMA.Text = Format(CARGA_MAX, "#####")
            End If
            '*********************************************
            '*********************************************
            If valor_carga > CARGA_MAX - 10 Then
                carga.ForeColor = &H8000&
            Else
                carga.ForeColor = &HFF&
            End If
            '*********************************************

    End If
End If
    
  If AiVolIn.chan = 1 Then
        canal(1, contador_lecturas) = voltage
        If contador_lecturas = numero_lecturas Then
            contador_lecturas = 0
            canal(1, 0) = 0
            For I = 1 To numero_lecturas
                canal(1, 0) = canal(1, 0) + canal(1, I)
            Next I
            
            canal(1, 0) = canal(1, 0) / numero_lecturas
            valor_deformacion = (canal(1, 0) - corrige1) * Constante_deformacion
            taracanal1 = canal(1, 0)
            deformacion.Text = Format(valor_deformacion, "###0.00")
            If valor_deformacion > DEFORMACION_MAX Then DEFORMACION_MAX = valor_deformacion
            DEFORMACION_MAXIMA.Text = Format(DEFORMACION_MAX, "###0.00")
                
            If voltage < -4.95 Or voltage > 4.95 Then
                    deformacion.BackColor = &H8080FF
            Else
                    deformacion.BackColor = &H80000005
            End If
           
            If inicio_tarado = "si" Then
                tara_canal = True
                lectotal = 0
            End If
                
            lectotal = lectotal + 1
        End If
    End If
    
End Sub

Private Sub tara_canal_Click()

    iniciar.Enabled = True
    parar.Enabled = False
    Reset.Enabled = False

    
If inicio_tarado <> "si" Then
    inicio_tarado = "si"
    numero_lecturas = 100
Else
    corrige0 = taracanal0
    corrige1 = taracanal1
    CARGA_MAX = 0
    DEFORMACION_MAX = 0
    numero_lecturas = 10
    inicio_tarado = "no"
End If


End Sub
