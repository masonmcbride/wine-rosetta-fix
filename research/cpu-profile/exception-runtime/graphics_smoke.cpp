// SPDX-License-Identifier: MIT
// Offscreen resource-copy smoke test; no window, swapchain, shaders or gameplay.
#define COBJMACROS
#include <windows.h>
#include <d3d11.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

using CreateDevice = HRESULT (WINAPI *)(IDXGIAdapter *, D3D_DRIVER_TYPE, HMODULE,
    UINT, const D3D_FEATURE_LEVEL *, UINT, UINT, ID3D11Device **,
    D3D_FEATURE_LEVEL *, ID3D11DeviceContext **);

static int fail(const char *stage, HRESULT hr) {
  printf("{\"passed\":false,\"stage\":\"%s\",\"hr\":\"0x%08lx\"}\n", stage, (unsigned long)hr);
  return 1;
}
int main(int argc, char **argv) {
  if (argc != 2 && argc != 3) return 2;
  if (!SetDllDirectoryA(argv[1])) return fail("dll_directory", HRESULT_FROM_WIN32(GetLastError()));
  char path[1024];
  if (snprintf(path, sizeof(path), "%s\\d3d11.dll", argv[1]) >= (int)sizeof(path)) return 3;
  HMODULE dll = LoadLibraryA(path);
  if (!dll) return fail("load_d3d11", HRESULT_FROM_WIN32(GetLastError()));
  CreateDevice create = (CreateDevice)GetProcAddress(dll, "D3D11CreateDevice");
  if (!create) return fail("find_create_device", HRESULT_FROM_WIN32(GetLastError()));
  ID3D11Device *device = nullptr;
  ID3D11DeviceContext *context = nullptr;
  D3D_FEATURE_LEVEL level;
  HRESULT hr = create(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0,
                      D3D11_SDK_VERSION, &device, &level, &context);
  if (FAILED(hr)) return fail("create_device", hr);
  unsigned char input[4096];
  for (unsigned i = 0; i < sizeof(input); ++i) input[i] = (unsigned char)((i * 37 + 11) & 255);
  D3D11_BUFFER_DESC desc = {};
  desc.ByteWidth = sizeof(input);
  desc.Usage = D3D11_USAGE_DEFAULT;
  desc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
  D3D11_SUBRESOURCE_DATA data = {};
  data.pSysMem = input;
  ID3D11Buffer *source = nullptr, *staging = nullptr;
  hr = device->CreateBuffer(&desc, &data, &source);
  if (FAILED(hr)) return fail("create_source", hr);
  desc.Usage = D3D11_USAGE_STAGING;
  desc.BindFlags = 0;
  desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
  hr = device->CreateBuffer(&desc, nullptr, &staging);
  if (FAILED(hr)) return fail("create_staging", hr);
  context->CopyResource(staging, source);
  D3D11_MAPPED_SUBRESOURCE mapped = {};
  hr = context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped);
  if (FAILED(hr)) return fail("map_staging", hr);
  bool matches = memcmp(input, mapped.pData, sizeof(input)) == 0;
  context->Unmap(staging, 0);
  staging->Release();
  const UINT stride = 16, offset = 32;
  context->IASetVertexBuffers(0, 1, &source, &stride, &offset);
  UINT actual_stride = 0, actual_offset = 0;
  context->IAGetVertexBuffers(0, 1, nullptr, &actual_stride, &actual_offset);
  if (actual_stride != stride || actual_offset != offset) return fail("vertex_state", E_FAIL);
  if (argc == 3) {
    const unsigned iterations = strtoul(argv[2], nullptr, 10);
    if (iterations < 10000 || iterations > 10000000) return 4;
    for (unsigned i = 0; i < 10000; ++i)
      context->IAGetVertexBuffers(0, 1, nullptr, &actual_stride, &actual_offset);
    LARGE_INTEGER frequency, begin, end;
    if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0) return 5;
    if (!QueryPerformanceCounter(&begin)) return 6;
    for (unsigned i = 0; i < iterations; ++i)
      context->IAGetVertexBuffers(0, 1, nullptr, &actual_stride, &actual_offset);
    if (!QueryPerformanceCounter(&end)) return 7;
    if (actual_stride != stride || actual_offset != offset) return fail("timed_vertex_state", E_FAIL);
    printf("{\"benchmark\":\"IAGetVertexBuffers\",\"iterations\":%u,"
           "\"ticks\":%lld,\"frequency\":%lld}\n", iterations,
           (long long)(end.QuadPart - begin.QuadPart), (long long)frequency.QuadPart);
  }
  source->Release();
  context->ClearState(); context->Flush();
  context->Release(); device->Release();
  if (!matches) return fail("copy_bytes", E_FAIL);
  char loaded[1024] = {};
  GetModuleFileNameA(dll, loaded, sizeof(loaded));
  // Emit the path on a separate plain line, avoiding JSON escaping ambiguity.
  printf("loaded_d3d11=%s\n", loaded);
  HMODULE dxgi = GetModuleHandleA("dxgi.dll");
  if (!dxgi || !GetModuleFileNameA(dxgi, loaded, sizeof(loaded)))
    return fail("locate_dxgi", HRESULT_FROM_WIN32(GetLastError()));
  printf("loaded_dxgi=%s\n", loaded);
  printf("{\"passed\":true,\"feature_level\":%u,\"copy_bytes\":4096}\n", (unsigned)level);
  FreeLibrary(dll);
  return 0;
}
