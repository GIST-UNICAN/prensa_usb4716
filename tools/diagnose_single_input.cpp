// Independent SDK probe: one input only, no GUI, Python bridge or filtering.
#include <windows.h>
#include <cstdio>
#include <cwchar>
#include <chrono>
#include <thread>
#include "bdaqctrl.h"
using namespace Automation::BDaq;
int wmain(int argc, wchar_t** argv) {
    const int channel = argc > 1 ? _wtoi(argv[1]) : 2;
    if (channel != 0 && channel != 2) return 2;
    InstantAiCtrl* ai = InstantAiCtrl::Create();
    if (!ai) return 3;
    ErrorCode rc = ai->setSelectedDevice(DeviceInformation(L"USB-4716,BID#0"));
    if (rc != Success) { fprintf(stderr,"Open: 0x%08X\n",(unsigned)rc); ai->Dispose(); return 4; }
    auto channels = ai->getChannels();
    rc = channels->getItem(channel).setSignalType(Differential);
    if (rc == Success) rc = channels->getItem(channel).setValueRange(V_Neg5To5);
    if (rc != Success) { fprintf(stderr,"Configure: 0x%08X\n",(unsigned)rc); ai->Dispose(); return 5; }
    fprintf(stderr,"AI%d: differential=%d, range_neg5to5=%d\n",channel,
        channels->getItem(channel).getSignalType()==Differential,
        channels->getItem(channel).getValueRange()==V_Neg5To5);
    puts("tiempo_s,voltaje_V");
    const auto start = std::chrono::steady_clock::now();
    for (int i=0; i<412; ++i) {
        double volts=0;
        rc=ai->Read(channel,volts);
        if (rc!=Success) { fprintf(stderr,"Read: 0x%08X\n",(unsigned)rc); ai->Dispose(); return 6; }
        const double t=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        printf("%.9f,%.9f\n",t,volts);
        std::this_thread::sleep_until(start+std::chrono::microseconds((i+1)*1000000/137));
    }
    ai->Dispose();
    return 0;
}
