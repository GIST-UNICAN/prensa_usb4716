Attribute VB_Name = "Module2"
Global Const MaxEntries = 255
Global DeviceHandle As Long
Global ptDevGetFeatures As PT_DeviceGetFeatures
Global lpDevFeatures As DEVFEATURES
Global devicelist(0 To MaxEntries) As PT_DEVLIST
Global SubDevicelist(0 To MaxEntries) As PT_DEVLIST
Global ErrCde As Long
Global szErrMsg As String * 80
Global bRun As Boolean

Global lpAIConfig As PT_AIConfig
Global AiVolIn As PT_AIVoltageIn
Global ptAIGetConfig As PT_AIGetConfig
Global AiCtrMode As Integer
