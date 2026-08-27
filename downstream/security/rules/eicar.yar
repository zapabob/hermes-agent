rule Hermes_EICAR_Antivirus_Test_File
{
    meta:
        description = "EICAR anti-malware pipeline validation file"
        author = "Hermes Agent"
        hermes_tier = "core"
    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" ascii
    condition:
        filesize == 68 and $eicar at 0
}
