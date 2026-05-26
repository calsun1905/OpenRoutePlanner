from gtfs_shapes import download_and_parse_shapes
print('Import OK, downloading shapes...')
shapes = download_and_parse_shapes(force=True)
print(f'Total shapes: {len(shapes)}')
if shapes:
    for k, v in list(shapes.items())[:5]:
        print(f'  {k}: {len(v)} points')