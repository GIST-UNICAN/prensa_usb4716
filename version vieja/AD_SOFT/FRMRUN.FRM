VERSION 5.00
Begin VB.Form frmRun 
   Appearance      =   0  'Flat
   BackColor       =   &H80000005&
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Analog Input Demo"
   ClientHeight    =   5904
   ClientLeft      =   2112
   ClientTop       =   1500
   ClientWidth     =   7368
   BeginProperty Font 
      Name            =   "MS Sans Serif"
      Size            =   7.8
      Charset         =   0
      Weight          =   700
      Underline       =   0   'False
      Italic          =   0   'False
      Strikethrough   =   0   'False
   EndProperty
   ForeColor       =   &H80000008&
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   PaletteMode     =   1  'UseZOrder
   ScaleHeight     =   5904
   ScaleWidth      =   7368
   Begin VB.TextBox carga 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   39.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   1035
      Left            =   360
      Locked          =   -1  'True
      TabIndex        =   3
      Text            =   "0.000"
      Top             =   3720
      Width           =   2532
   End
   Begin VB.Timer tmrRead 
      Left            =   0
      Top             =   1200
   End
   Begin VB.TextBox txtVoltRead1 
      Alignment       =   2  'Center
      Appearance      =   0  'Flat
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   39.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   1035
      Left            =   240
      Locked          =   -1  'True
      TabIndex        =   1
      Text            =   "0.000"
      Top             =   360
      Width           =   2532
   End
   Begin VB.CommandButton cmdExit 
      Appearance      =   0  'Flat
      BackColor       =   &H80000005&
      Caption         =   "E&xit"
      Height          =   495
      Left            =   4320
      TabIndex        =   0
      Top             =   840
      Width           =   1455
   End
   Begin VB.Label labVolt 
      Appearance      =   0  'Flat
      BackColor       =   &H80000005&
      Caption         =   "Voltage read"
      ForeColor       =   &H80000008&
      Height          =   255
      Left            =   600
      TabIndex        =   2
      Top             =   120
      Width           =   1215
   End
End
Attribute VB_Name = "frmRun"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

Private Sub cmdExit_Click()
    frmRun.Hide
    frmDevSel.Show
    frmDevSel.cmdExit.SetFocus
End Sub



Private Sub cmdRead_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    shapLed.FillColor = QBColor(12)
End Sub

Private Sub Form_Load()
  hscrlFreq_Change
End Sub

Private Sub Form_Unload(Cancel As Integer)
    frmDevSel.Show
End Sub

Private Sub hscrlFreq_Change()
    'If hscrlFreq.value = 0 Then
       ' tmrRead.Interval = 0
    'Else
       ' tmrRead.Interval = 10000 / hscrlFreq.value
    'End If
    tmrRead.Interval = 1
'    hscrlFreq.value = 100
    'txtSample.Text = Format((hscrlFreq.value / 10), "###0.00")
    ' "Read One Shot" would disable the "trmREAD" Timer,
    ' so it need to enable here.
    'tmrRead.Enabled = True
    'tmrLed.Enabled = True
End Sub

Private Sub tmrLed_Timer()
    'shapLed.FillColor = QBColor(8)
End Sub

Private Sub tmrRead_Timer()
  Dim voltage As Single
  'El numero de lecturas por segundo zse obtiene dividiendo
  '1000 entre tmrRead
   'tmrRead.Interval = 10
  'shapLed.FillColor = QBColor(12)
  lpAIConfig.DasChan = 0
  
  
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
  UpDateValue (voltage)
End Sub

Private Sub UpDateValue(fValue As Single)

    ' Since the output box is too small to display all the digits
    ' of the input voltage, so it must use to format to get better
    ' display.
    txtVoltRead1.Text = Format(fValue, "###0.000")
End Sub

Private Sub txtSample_Change()

End Sub

Private Sub txtVoltRead1_Click()
  tmrRead.Enabled = True
  'tmrLed.Enabled = True
End Sub


