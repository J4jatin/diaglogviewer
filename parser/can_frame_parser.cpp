/**
 * CAN Frame Parser — C++ low-level decoder
 *
 * Decodes raw CAN frames: OBD-II PIDs, UDS services, J1939 PGNs.
 * Called from Python via subprocess: ./can_frame_parser <CAN_ID> <byte0> <byte1> ...
 *
 * Build: g++ -O2 -std=c++17 -o can_frame_parser can_frame_parser.cpp
 */

#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <iomanip>
#include <map>
#include <algorithm>
#include <cstdint>

// ── UDS Service ID map ────────────────────────────────────────────────────────
static const std::map<uint8_t, std::string> UDS_SERVICES = {
    {0x10, "DiagnosticSessionControl"},
    {0x11, "ECUReset"},
    {0x14, "ClearDiagnosticInformation"},
    {0x19, "ReadDTCInformation"},
    {0x22, "ReadDataByIdentifier"},
    {0x23, "ReadMemoryByAddress"},
    {0x27, "SecurityAccess"},
    {0x28, "CommunicationControl"},
    {0x2E, "WriteDataByIdentifier"},
    {0x2F, "InputOutputControlByIdentifier"},
    {0x31, "RoutineControl"},
    {0x34, "RequestDownload"},
    {0x35, "RequestUpload"},
    {0x36, "TransferData"},
    {0x37, "RequestTransferExit"},
    {0x3E, "TesterPresent"},
    {0x50, "DiagnosticSessionControl_Resp"},
    {0x51, "ECUReset_Resp"},
    {0x59, "ReadDTCInformation_Resp"},
    {0x62, "ReadDataByIdentifier_Resp"},
    {0x67, "SecurityAccess_Resp"},
    {0x6E, "WriteDataByIdentifier_Resp"},
    {0x71, "RoutineControl_Resp"},
    {0x74, "RequestDownload_Resp"},
    {0x76, "TransferData_Resp"},
    {0x7E, "TesterPresent_Resp"},
    {0x7F, "NegativeResponse"},
};

// ── OBD-II PID descriptions ───────────────────────────────────────────────────
static const std::map<uint8_t, std::string> OBD_PIDS = {
    {0x00, "Supported PIDs 01-20"},
    {0x04, "Engine Load"},
    {0x05, "Coolant Temperature"},
    {0x0B, "Intake Manifold Pressure"},
    {0x0C, "Engine RPM"},
    {0x0D, "Vehicle Speed"},
    {0x0F, "Intake Air Temperature"},
    {0x10, "Mass Air Flow"},
    {0x11, "Throttle Position"},
    {0x1C, "OBD Standards"},
    {0x2F, "Fuel Tank Level"},
    {0x31, "Distance since DTC cleared"},
    {0x46, "Ambient Temperature"},
    {0x5A, "Accelerator Pedal Position"},
};

// ── J1939 PGN descriptions ────────────────────────────────────────────────────
static const std::map<uint32_t, std::string> J1939_PGNS = {
    {0xF004, "Electronic Engine Controller 1"},
    {0xFEF1, "Cruise Control/Vehicle Speed"},
    {0xFEF2, "Fuel Economy"},
    {0xFEF6, "Inlet/Exhaust Conditions"},
    {0xFF00, "Proprietary A"},
};

// ── Helpers ───────────────────────────────────────────────────────────────────
static uint32_t parseHex(const std::string& s) {
    uint32_t val = 0;
    std::istringstream ss(s);
    ss >> std::hex >> val;
    return val;
}

static std::string toHexStr(uint8_t b) {
    std::ostringstream ss;
    ss << "0x" << std::uppercase << std::hex << std::setw(2) << std::setfill('0') << (int)b;
    return ss.str();
}

// ── Decoders ──────────────────────────────────────────────────────────────────
std::string decodeUDS(const std::vector<uint8_t>& data) {
    if (data.size() < 2) return "";
    // ISO 15765-2 single frame: byte[0] = length, byte[1] = service ID
    uint8_t sid = data[1];
    auto it = UDS_SERVICES.find(sid);
    if (it == UDS_SERVICES.end()) return "";
    std::string result = "UDS " + it->second + " (" + toHexStr(sid) + ")";
    // Negative response detail
    if (sid == 0x7F && data.size() >= 4) {
        auto nrc_it = UDS_SERVICES.find(data[2]);
        std::string req = (nrc_it != UDS_SERVICES.end()) ? nrc_it->second : toHexStr(data[2]);
        result += " for " + req + " NRC=" + toHexStr(data[3]);
    }
    return result;
}

std::string decodeOBD(uint32_t can_id, const std::vector<uint8_t>& data) {
    // OBD-II functional request: 0x7DF or ECU response: 0x7E8-0x7EF
    bool is_request  = (can_id == 0x7DF);
    bool is_response = (can_id >= 0x7E8 && can_id <= 0x7EF);
    if (!is_request && !is_response) return "";
    if (data.size() < 3) return "";

    uint8_t mode = data[1];
    uint8_t pid  = data[2];

    std::string prefix = is_response ? "OBD Response" : "OBD Request";
    std::string mode_str = (mode == 0x01) ? "CurrentData" :
                           (mode == 0x02) ? "FreezeFrame" :
                           (mode == 0x03) ? "StoredDTCs" :
                           (mode == 0x04) ? "ClearDTCs" :
                           (mode == 0x41) ? "CurrentData_Resp" : toHexStr(mode);

    auto pid_it = OBD_PIDS.find(pid);
    std::string pid_str = (pid_it != OBD_PIDS.end()) ? pid_it->second : toHexStr(pid);

    // Decode numeric values for common PIDs
    std::string value;
    if (is_response && mode == 0x41 && data.size() >= 4) {
        if (pid == 0x05) {
            value = " = " + std::to_string(data[3] - 40) + " °C";
        } else if (pid == 0x0C && data.size() >= 5) {
            uint16_t rpm = ((uint16_t)data[3] << 8 | data[4]) / 4;
            value = " = " + std::to_string(rpm) + " RPM";
        } else if (pid == 0x0D) {
            value = " = " + std::to_string(data[3]) + " km/h";
        } else if (pid == 0x04) {
            value = " = " + std::to_string(data[3] * 100 / 255) + " %";
        }
    }

    return prefix + " Mode=" + mode_str + " PID=" + pid_str + value;
}

std::string decodeJ1939(uint32_t can_id, const std::vector<uint8_t>& data) {
    // J1939 uses 29-bit extended IDs > 0x10000000
    if (can_id < 0x08000000) return "";
    uint32_t pgn = (can_id >> 8) & 0x3FFFF;
    auto it = J1939_PGNS.find(pgn & 0xFF00);
    if (it == J1939_PGNS.end()) it = J1939_PGNS.find(pgn);
    if (it == J1939_PGNS.end()) return "";
    std::ostringstream ss;
    ss << "J1939 PGN=0x" << std::uppercase << std::hex << pgn
       << " (" << it->second << ")";
    return ss.str();
}

// ── Main ──────────────────────────────────────────────────────────────────────
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: can_frame_parser <CAN_ID_hex> [byte0_hex byte1_hex ...]\n";
        return 1;
    }

    uint32_t can_id = parseHex(std::string(argv[1]));
    std::vector<uint8_t> data;
    for (int i = 2; i < argc; ++i) {
        data.push_back(static_cast<uint8_t>(parseHex(std::string(argv[i]))));
    }

    // Try decoders in priority order
    std::string result;

    result = decodeUDS(data);
    if (!result.empty()) { std::cout << result << "\n"; return 0; }

    result = decodeOBD(can_id, data);
    if (!result.empty()) { std::cout << result << "\n"; return 0; }

    result = decodeJ1939(can_id, data);
    if (!result.empty()) { std::cout << result << "\n"; return 0; }

    // Generic fallback
    std::ostringstream ss;
    ss << "CAN ID=0x" << std::uppercase << std::hex << can_id << " DLC=" << data.size() << " DATA=";
    for (size_t i = 0; i < data.size(); ++i) {
        if (i) ss << " ";
        ss << std::uppercase << std::hex << std::setw(2) << std::setfill('0') << (int)data[i];
    }
    std::cout << ss.str() << "\n";
    return 0;
}
