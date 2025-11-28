section .data
fmt_int: db "%ld", 10, 0
fmt_read: db "%ld", 0
.Lstr0: db "HELLO WORLD!",0
.Lstr1: db "WHAT'S YOUR NAME?",0
.Lstr2: db "HELLO,",0

section .bss
mem: resq 4

section .text
global main
extern printf, scanf, puts

main:
    push rbp
    mov rbp, rsp
    lea rdi, [rel .Lstr0]
    call puts
    lea rdi, [rel .Lstr1]
    call puts
    lea rdi, [rel fmt_read]
    lea rsi, [rel mem + 8]
    xor rax, rax
    call scanf
    lea rax, [rel .Lstr2]
    mov rbx, [rel mem + 8]
    add rax, rbx
    mov [rel mem + 24], rax
    mov rsi, [rel mem + 24]
    lea rdi, [rel fmt_int]
    xor rax, rax
    call printf
    mov rsp, rbp
    pop rbp
    ret
