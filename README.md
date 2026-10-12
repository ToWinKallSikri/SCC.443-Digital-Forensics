# SCC.443 Digital Forensics

Coursework for **SCC.443 Digital Forensics**, part of my MSc Cyber Security at Lancaster University. The repository holds two investigations, each set as a fictional case for the fictional firm ACME Forensics:

| Part | What it is | Main skills |
|---|---|---|
| [FAT16 Disk Recovery](#1-fat16-disk-recovery-python) | A Python tool that rebuilds files from a FAT16 disk image whose root directory has been wiped | File-system internals, binary parsing, evidence integrity |
| [Network Forensics Report](#2-network-forensics-report) | A full incident investigation of a data breach and ransomware attack using a packet capture and its key log | Wireshark, host identification, incident reconstruction, UK legal analysis |

> All people, companies and data in these cases are fictional and were provided by the module for assessment.

---

## Repository structure

```
.
├── FAT16 - Disk Recovery/
│   ├── main.py                     # Entry point: parses the image and recovers files
│   ├── fat_base.py                 # FAT16 boot-sector parsing and cluster helpers
│   ├── fat16-37078169-38.img       # Disk image analysed by main.py
│   ├── fat16-36928224-14.img       # Second disk image with the same structure
│   ├── RecoveredFiles/             # The 57 files recovered by the tool
│   ├── README.txt                  # Original submission notes
│   └── SCC_443___Prorgramming_Asssignment_Report.pdf
├── SCC_443___Digital_Forensics___Tools_Report.pdf
└── LICENSE
```

---

## 1. FAT16 Disk Recovery (Python)

### The problem
A suspect had wiped the **root directory** of a FAT16 disk image, so tools that start from the root can't find any files. The data clusters and the File Allocation Tables (FATs) were still intact.

### How the tool works
The tool reads the raw image byte by byte and uses only the Python standard library (`struct`, `os`, `sys`).

1. **Boot sector parsing:** reads the BIOS Parameter Block (bytes per sector, sectors per cluster, reserved sectors, number of FATs, root entry count, FAT size) and works out the layout: the reserved area, FAT1 and FAT2, the root directory region and the data region.
2. **Integrity checks:** confirms the root directory is empty (all zero bytes, so it was wiped) and compares FAT1 with FAT2 byte by byte to check whether they had been tampered with.
3. **Orphaned directory discovery:** scans every data cluster for directory signatures (the `.` and `..` entries) to find directory chains that are no longer linked to the root. On the analysed image it finds **8 orphaned directory chains and 16 subdirectories**.
4. **Entry parsing:** reads each 32-byte directory entry (8.3 short name, attributes, first cluster, file size). It skips long file name (LFN), deleted, volume-label and `.`/`..` entries.
5. **File reconstruction:** follows each file's cluster chain through the FAT until the end-of-chain marker (`>= 0xFFF8`), joins the clusters together and cuts the data to the exact file size recorded in the directory entry.
6. **Output:** writes each file to `RecoveredFiles/` and prints its name, starting cluster and size.

### Results
- **57 files recovered** from `fat16-37078169-38.img`, including Linux manual pages, `dpkg` documentation and two files relevant to the case: `INVOICE.PDF` and a cryptocurrency transaction record (`TRANSA~1.TXT`).
- **FAT1 and FAT2 are identical**, so the allocation tables had not been tampered with.
- **The image's MD5 hash (`566ea56db767c62c9dab8794d9b260e5`)** matches the chain-of-custody record, so the evidence had not changed.

### How to run
You need Python 3 (it was developed with Python 3.13). There are no third-party dependencies.

```bash
cd "FAT16 - Disk Recovery"
python3 main.py
```

Run it from inside the folder, because the image path and the `RecoveredFiles/` output folder are relative to the working directory. To analyse the second image, change `img_path` in `main.py` to `fat16-36928224-14.img`.

Sample output:

```
Root directory is empty - possibly wiped
Both FATs are the same.
Found 8 orphaned directory chains and 16 sub-directories
Saved: DPKG-D~1.1           | Cluster:      4 | Size:       2285 bytes
...
Saved: INVOICE.PDF          | Cluster:    942 | Size:     111093 bytes
Saved: TRANSA~1.TXT         | Cluster:    997 | Size:        218 bytes
Successfully saved 57 files.
```

### Limitations
- It recovers short 8.3 file names only, because long file name entries are skipped.
- It doesn't try to recover deleted directory entries (`0xE5`).
- It uses FAT1 for cluster chains, which is safe here because FAT1 and FAT2 were confirmed to be identical.

The full method and findings are in the [programming assignment report](FAT16%20-%20Disk%20Recovery/SCC_443___Prorgramming_Asssignment_Report.pdf).

---

## 2. Network Forensics Report

[`SCC_443___Digital_Forensics___Tools_Report.pdf`](SCC_443___Digital_Forensics___Tools_Report.pdf)

A forensic investigation, written as an ACME Forensics report, into a data breach and ransomware attack at a fictional confectionery company, **Terry's Digital**. The evidence was a packet capture (`3e547-CAPTURE.pcap`) and the key log supplied with it (`3e547-KEYS.log`).

### Method
- **Evidence handling:** hashed the evidence with MD5 on receipt, kept a verified backup copy, and hashed every extracted artefact (screenshots, emails, scripts, encrypted files and exported streams).
- **Context and host identification:** read the email exchanges in the capture to build two host tables, one of internal hosts and one of endpoints involved in suspicious traffic.
- **Analysis:** worked manually through TCP, TLS, UDP, HTTP and DNS streams to spot unusual or malicious traffic, then saved the relevant streams and files (emails, images, scripts, encrypted `.locked` files) as evidence.
- **Decoding and reputation checks:** decoded content with CyberChef and checked suspicious IP addresses and domains on VirusTotal.
- **Tools:** Wireshark 4.2.2, CyberChef 10.22.1 (a local Docker instance), VirusTotal and `md5sum` on Ubuntu.

### Findings
- **Data leak:** customer PII and payment-card (PCI) data was found exposed on dark-web pages, and sensitive data had been handled over unencrypted channels.
- **Ransomware:** files on the web server were renamed with a `.locked` extension and a ransom note demanding payment in cryptocurrency appeared on the site's main page. The requests were traced back to a machine on the internal network.
- **Keylogger:** an employee downloaded and ran a PowerShell script disguised as a dump file. It was actually a keylogger that sent keystrokes in 50-character chunks through DNS queries to an attacker-controlled domain.
- **Insider risk:** employees accessed confidential PCI directories, used offensive security tools (Nmap, Zenmap, Metasploit, Hydra, ZAP, SSLyze), sent login details in cleartext, and one discussed leaking company data with an AI chatbot.
- **Conclusion:** the capture doesn't show one clear chain of events behind the compromise, but the lack of security policies and controls left the company open to attackers.

### Legal analysis
The report ends with an expert opinion on liability under UK law:
- **Computer Misuse Act 1990:** s.1(1) unauthorised access and s.3(1) impairing a computer's operation.
- **UK GDPR:** Article 32(1)(b) security of processing and Article 5(1)(f) integrity and confidentiality.
- **Data Protection Act 2018:** s.170 unlawfully obtaining personal data.
- **Employer liability:** the company's exposure to ICO enforcement for employee negligence.

> The raw capture and extracted evidence files are not in this repository. Their MD5 hashes are listed in Appendix A of the report.

---

## Skills demonstrated
- Low-level analysis of the FAT16 file system and recovery of files without directory metadata
- Binary parsing in Python with `struct`
- Network forensics: stream analysis across TCP, TLS, UDP, HTTP and DNS, plus evidence extraction in Wireshark
- Evidence integrity and chain of custody using MD5 hashing and verification
- Incident reconstruction and professional forensic reporting
- Applying UK cyber and data protection law (CMA 1990, UK GDPR, DPA 2018)

## Author
**Twinkal Sikri**, MSc Cyber Security, Lancaster University
[Portfolio](https://towinkallsikri.github.io) · [LinkedIn](https://www.linkedin.com/in/twinkal-sikri-a167a6327)

## Licence
Released under the [MIT License](LICENSE).
