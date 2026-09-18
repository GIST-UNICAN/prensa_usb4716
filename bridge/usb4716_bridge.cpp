// DLL puente: Python/Tkinter <-> Advantech DAQNavi (Automation::BDaq)
// Compilar en Windows x64 con el DAQNavi SDK instalado.
#include <windows.h>
#include <initializer_list>
#include "bdaqctrl.h"

using namespace Automation::BDaq;

static InstantAiCtrl* g_ai = nullptr;
static int g_force_ch = 0;
static int g_deform_ch = 2;

extern "C" __declspec(dllexport) int __cdecl daq_open(const wchar_t* deviceDescription,
                                                       int forceChannel,
                                                       int deformationChannel)
{
    if (g_ai != nullptr) return -4;
    // Canales fisicos positivos de pares consecutivos; nunca reutilizar el retorno.
    if (forceChannel < 0 || forceChannel > 14 || (forceChannel % 2) ||
        deformationChannel < 0 || deformationChannel > 14 || (deformationChannel % 2) ||
        forceChannel == deformationChannel) return -2;
    g_force_ch = forceChannel;
    g_deform_ch = deformationChannel;

    g_ai = InstantAiCtrl::Create();
    if (g_ai == nullptr) return -1;

    DeviceInformation devInfo(deviceDescription);
    ErrorCode ret = g_ai->setSelectedDevice(devInfo);
    if (ret != Success) {
        g_ai->Dispose();
        g_ai = nullptr;
        return (int)ret;
    }

    // Replicamos el sistema antiguo: entradas diferenciales, rango +/-5 V.
    // Para USB-4716, por defecto se usan pares AI0-AI1 y AI2-AI3; por eso
    // la app utiliza canales logicos 0 y 2, configurables en config.json.
    Array<AiChannel>* channels = g_ai->getChannels();
    const int count = g_ai->getChannelCount();
    if (g_force_ch < 0 || g_force_ch >= count || g_deform_ch < 0 || g_deform_ch >= count) {
        g_ai->Dispose(); g_ai = nullptr; return -2;
    }

    ret = channels->getItem(g_force_ch).setSignalType(Differential);
    if (ret != Success) { g_ai->Dispose(); g_ai = nullptr; return (int)ret; }
    ret = channels->getItem(g_force_ch).setValueRange(V_Neg5To5);
    if (ret != Success) { g_ai->Dispose(); g_ai = nullptr; return (int)ret; }

    ret = channels->getItem(g_deform_ch).setSignalType(Differential);
    if (ret != Success) { g_ai->Dispose(); g_ai = nullptr; return (int)ret; }
    ret = channels->getItem(g_deform_ch).setValueRange(V_Neg5To5);
    if (ret != Success) { g_ai->Dispose(); g_ai = nullptr; return (int)ret; }

    // Verificar los ajustes efectivos, no depender del perfil previo de Navigator.
    for (int channel : {g_force_ch, g_deform_ch}) {
        if (channels->getItem(channel).getSignalType() != Differential ||
            channels->getItem(channel).getValueRange() != V_Neg5To5) {
            g_ai->Dispose(); g_ai = nullptr; return -5;
        }
    }
    return 0;
}

extern "C" __declspec(dllexport) int __cdecl daq_read_two(double* forceVoltage,
                                                           double* deformationVoltage)
{
    if (g_ai == nullptr || forceVoltage == nullptr || deformationVoltage == nullptr) return -3;
    ErrorCode ret = g_ai->Read(g_force_ch, *forceVoltage);
    if (ret != Success) return (int)ret;
    ret = g_ai->Read(g_deform_ch, *deformationVoltage);
    if (ret != Success) return (int)ret;
    return 0;
}

extern "C" __declspec(dllexport) void __cdecl daq_close()
{
    if (g_ai != nullptr) {
        g_ai->Dispose();
        g_ai = nullptr;
    }
}
