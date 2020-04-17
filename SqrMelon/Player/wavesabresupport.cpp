#define _CRT_SECURE_NO_WARNINGS
#define WIN32_LEAN_AND_MEAN
#define VC_EXTRALEAN
#include "wglext.h"

#include "settings.h"

extern "C"
{
    IID GUID_NULL;
    int _purecall() { return 0; };
}


#ifdef AUDIO_WAVESABRE


void* __cdecl operator new(unsigned int x) { return HeapAlloc(GetProcessHeap(), 0, x); }
void* __cdecl operator new[](unsigned int x) { return HeapAlloc(GetProcessHeap(), 0, x); }
#pragma function(memcpy)
extern "C" void* __cdecl memcpy(void* dst, const void* src, size_t count) { count--; do { ((char*)dst)[count] = ((char*)src)[count]; } while (count--); return dst; }
#pragma function(memset)
extern "C" void* __cdecl memset(void *dest, int c, size_t count) { char *bytes = (char *)dest; while (count--) { *bytes++ = (char)c; } return dest; }



//https://hero.handmade.network/forums/code-discussion/t/94-guide_-_how_to_avoid_c_c++_runtime_on_windows
//https://gist.github.com/mmozeiko/6a365d6c483fc721b63a#file-win32_crt_math-cpp


extern "C" __declspec(naked) void __cdecl _ftol2_sse()
{
    __asm
    {
        fistp dword ptr[esp - 4]
        mov   eax, [esp - 4]
        ret
    }
}

extern "C" __declspec(naked) void __cdecl _allshl(void)
{
    __asm {
        // Handle shifts of 64 or more bits (all get 0)
        cmp     cl, 64
        jae     short RETZERO
        // Handle shifts of between 0 and 31 bits
        cmp     cl, 32
        jae     short MORE32
        shld    edx, eax, cl
        shl     eax, cl
        ret
        // Handle shifts of between 32 and 63 bits
        MORE32 :
        mov     edx, eax
            xor     eax, eax
            and     cl, 31
            shl     edx, cl
            ret
            // return 0 in edx:eax
            RETZERO :
        xor     eax, eax
            xor     edx, edx
            ret
    }
}

#define CRT_LOWORD(x) dword ptr [x+0]
#define CRT_HIWORD(x) dword ptr [x+4]

extern "C" __declspec(naked) void __cdecl _alldiv()
{
#define DVND    esp + 16      // stack address of dividend (a)
#define DVSR    esp + 24      // stack address of divisor (b)

    __asm
    {
        push    edi
        push    esi
        push    ebx

        ; Determine sign of the result(edi = 0 if result is positive, non - zero
        ; otherwise) and make operands positive.

        xor     edi, edi; result sign assumed positive

        mov     eax, CRT_HIWORD(DVND); hi word of a
        or eax, eax; test to see if signed
        jge     short L1; skip rest if a is already positive
        inc     edi; complement result sign flag
        mov     edx, CRT_LOWORD(DVND); lo word of a
        neg     eax; make a positive
        neg     edx
        sbb     eax, 0
        mov     CRT_HIWORD(DVND), eax; save positive value
        mov     CRT_LOWORD(DVND), edx
        L1 :
        mov     eax, CRT_HIWORD(DVSR); hi word of b
            or eax, eax; test to see if signed
            jge     short L2; skip rest if b is already positive
            inc     edi; complement the result sign flag
            mov     edx, CRT_LOWORD(DVSR); lo word of a
            neg     eax; make b positive
            neg     edx
            sbb     eax, 0
            mov     CRT_HIWORD(DVSR), eax; save positive value
            mov     CRT_LOWORD(DVSR), edx
            L2 :

        ;
        ; Now do the divide.First look to see if the divisor is less than 4194304K.
            ; If so, then we can use a simple algorithm with word divides, otherwise
            ; things get a little more complex.
            ;
        ; NOTE - eax currently contains the high order word of DVSR
            ;

        or eax, eax; check to see if divisor < 4194304K
            jnz     short L3; nope, gotta do this the hard way
            mov     ecx, CRT_LOWORD(DVSR); load divisor
            mov     eax, CRT_HIWORD(DVND); load high word of dividend
            xor     edx, edx
            div     ecx; eax <-high order bits of quotient
            mov     ebx, eax; save high bits of quotient
            mov     eax, CRT_LOWORD(DVND); edx:eax <-remainder : lo word of dividend
            div     ecx; eax <-low order bits of quotient
            mov     edx, ebx; edx:eax <-quotient
            jmp     short L4; set sign, restore stack and return

            ;
        ; Here we do it the hard way.Remember, eax contains the high word of DVSR
            ;

    L3:
        mov     ebx, eax; ebx:ecx <-divisor
            mov     ecx, CRT_LOWORD(DVSR)
            mov     edx, CRT_HIWORD(DVND); edx:eax <-dividend
            mov     eax, CRT_LOWORD(DVND)
            L5 :
            shr     ebx, 1; shift divisor right one bit
            rcr     ecx, 1
            shr     edx, 1; shift dividend right one bit
            rcr     eax, 1
            or ebx, ebx
            jnz     short L5; loop until divisor < 4194304K
            div     ecx; now divide, ignore remainder
            mov     esi, eax; save quotient

            ;
        ; We may be off by one, so to check, we will multiply the quotient
            ; by the divisor and check the result against the orignal dividend
            ; Note that we must also check for overflow, which can occur if the
            ; dividend is close to 2 * *64 and the quotient is off by 1.
            ;

        mul     CRT_HIWORD(DVSR); QUOT * CRT_HIWORD(DVSR)
            mov     ecx, eax
            mov     eax, CRT_LOWORD(DVSR)
            mul     esi; QUOT * CRT_LOWORD(DVSR)
            add     edx, ecx; EDX:EAX = QUOT * DVSR
            jc      short L6; carry means Quotient is off by 1

            ;
        ; do long compare here between original dividend and the result of the
            ; multiply in edx : eax.If original is larger or equal, we are ok, otherwise
            ; subtract one(1) from the quotient.
            ;

        cmp     edx, CRT_HIWORD(DVND); compare hi words of result and original
            ja      short L6; if result > original, do subtract
            jb      short L7; if result < original, we are ok
            cmp     eax, CRT_LOWORD(DVND); hi words are equal, compare lo words
            jbe     short L7; if less or equal we are ok, else subtract
            L6 :
        dec     esi; subtract 1 from quotient
            L7 :
        xor     edx, edx; edx:eax <-quotient
            mov     eax, esi

            ;
        ; Just the cleanup left to do.edx:eax contains the quotient.Set the sign
            ; according to the save value, cleanup the stack, and return.
            ;

    L4:
        dec     edi; check to see if result is negative
            jnz     short L8; if EDI == 0, result should be negative
            neg     edx; otherwise, negate the result
            neg     eax
            sbb     edx, 0

            ;
        ; Restore the saved registers and return.
            ;

    L8:
        pop     ebx
            pop     esi
            pop     edi

            ret     16
    }

#undef DVND
#undef DVSR
}


extern "C" __declspec(naked) void __cdecl _allmul()
{
#define A       esp + 8       // stack address of a
#define B       esp + 16      // stack address of b

    __asm
    {
        push    ebx

        mov     eax, CRT_HIWORD(A)
        mov     ecx, CRT_LOWORD(B)
        mul     ecx;eax has AHI, ecx has BLO, so AHI * BLO
        mov     ebx, eax;save result

        mov     eax, CRT_LOWORD(A)
        mul     CRT_HIWORD(B);ALO * BHI
        add     ebx, eax;ebx = ((ALO * BHI) + (AHI * BLO))

        mov     eax, CRT_LOWORD(A);ecx = BLO
        mul     ecx;so edx : eax = ALO * BLO
        add     edx, ebx;now edx has all the LO*HI stuff

        pop     ebx

        ret     16; callee restores the stack
    }

#undef A
#undef B
}

extern "C" __declspec(naked) void __cdecl _aullshr()
{
    __asm
    {
        cmp     cl, 64
        jae     short RETZERO
        ;
        ; Handle shifts of between 0 and 31 bits
            ;
        cmp     cl, 32
            jae     short MORE32
            shrd    eax, edx, cl
            shr     edx, cl
            ret
            ;
        ; Handle shifts of between 32 and 63 bits
            ;
    MORE32:
        mov     eax, edx
            xor     edx, edx
            and     cl, 31
            shr     eax, cl
            ret
            ;
        ; return 0 in edx : eax
            ;
    RETZERO:
        xor     eax, eax
            xor     edx, edx
            ret
    }
}



void __cdecl operator delete(void* p, unsigned int x) { HeapFree(GetProcessHeap(), 0, p); }
void __cdecl operator delete(void* p) { HeapFree(GetProcessHeap(), 0, p); }
void __cdecl operator delete[](void* p) { HeapFree(GetProcessHeap(), 0, p); }
void __cdecl operator delete[](void* p, unsigned int x) { HeapFree(GetProcessHeap(), 0, p); }


// https://docs.microsoft.com/nl-nl/cpp/c-runtime-library/internal-crt-globals-and-functions?view=vs-2017
// https://github.com/reactos/wine/blob/master/dlls/msvcrt/math.c


extern "C" void __cdecl _libm_sse2_sin_precise()
{
    double d;

    __asm
    {
        movq d, xmm0
        fld d
        fsin
        fstp d
        movq xmm0, d
    }
}

extern "C" void __cdecl _libm_sse2_cos_precise()
{
    double d;

    __asm
    {
        movq d, xmm0
        fld d
        fcos
        fstp d
        movq xmm0, d
    }
}

extern "C" void __cdecl _libm_sse2_tan_precise()
{
    double d;

    __asm
    { 
        movq d, xmm0
        fld d
        fsin
        fld d
        fcos                    // ST1=sin, ST0=cos
        fdivp ST(1), ST(0)       // ST0 = sin/cos
        fstp d
        movq xmm0, d
    }
}

extern "C" void __cdecl _libm_sse2_sqrt_precise()
{
    double d;

    __asm
    {
        movq d, xmm0
        fld d
        fsqrt
        fstp d
        movq xmm0, d
    }
}

extern "C" void __cdecl _libm_sse2_pow_precise()
{
    // d1 = pow(d1,d2)

    double d1, d2;
    __asm
    {
        movq d1, xmm0
        movq d2, xmm1

        fld d2
        fld d1
        fyl2x       // ST = y * log2(x)

        fld   st    // ST(1) = ST
        frndint     //  ST = integer part
        fsub  st(1), st // ST(1) = fractional part
        fxch  st(1)     // swap

        f2xm1           // compute result for fraction

        fld1            // correct for - 1 of f2xm1
        fadd

        fscale          // correct for integer part

        fstp  st(1)     // adjust stack

        fstp d1
        movq xmm0, d1
    }
}



extern "C" void __cdecl _libm_sse2_log10_precise()
{
    // d = log10(d)

    double d;
    __asm
    {
        movq d, xmm0

        fldlg2
        fld   d
        fyl2x

        fstp d
        movq xmm0, d
    }
}



#endif // AUDIO_WAVESABRE

