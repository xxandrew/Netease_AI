import requests, os
base = r'C:\Netease_Ai\project\ux-design-doc\case-social-0424\design'
imgs = [
    ('02-双人动作-右侧窗.png',    'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/0d93b64b-c779-4473-b6d2-95411c4a907b'),
    ('03-双人动作-等待确认.png',  'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/ea98831a-dd0f-4a36-8f07-2c062c27f797'),
    ('04-双人动作-同意.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/9d6c3d75-3f77-4075-86e8-1535d86e312c'),
    ('05-随行-发起.png',          'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/0dabefd7-04ce-4cc7-838f-8616a6bf3a6d'),
    ('06-随行-等待同意.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/c02fe499-3c73-4538-a394-0448fd1da53a'),
    ('07-随行-待机-发起方.png',   'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/6bd499ec-1690-472b-b399-a4e71373b6d8'),
    ('08-随行-待机-跟随方.png',   'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/40cc37af-8a1d-45c3-8a9e-a3b139ab0a27'),
    ('09-随行-发起方取消.png',    'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/a54dbe00-e97e-4dfc-91c2-9bd2a03ee40e'),
    ('10-随行-受邀方同意.png',    'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/00b0ec05-aff6-4da9-a1de-f55d7fb5a4c7'),
    ('11-随行-大幅摇杆取消.png',  'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/d13f35d6-b150-4c0c-8648-83d380048df6'),
    ('12-随行-小幅摇杆取消.png',  'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/84648cfb-a42b-4738-b9c4-e6dcefcd0693'),
    ('13-单人动作-发起.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/975a9d5e-888a-4988-89f9-66983d9cb81a'),
    ('14-单人动作-右侧窗.png',    'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/1c8e0cd6-fd4c-4b2d-a751-7e53ec5a2465'),
    ('15-单人切双人动作.png',     'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/09d19e16-cca7-4fad-88db-578e3a258746'),
    ('16-单人切双人提示.png',     'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/3c43d998-00df-4124-82b7-8a4d113efcc4'),
    ('17-聊天-点击聊天.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/fdd04fc4-ef7a-4507-9253-fa6e7880163c'),
    ('18-聊天-对话发出.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/b52ed8a1-61f4-49a0-89be-5efd28ba26ac'),
    ('19-聊天-键盘无字.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/cecf676b-3cf6-4da6-a54e-28b933aafc8b'),
    ('20-聊天-键盘有字.png',      'https://figma-alpha-api.s3.us-west-2.amazonaws.com/images/42c96a85-136a-45c8-a12a-6751f93e631b'),
]
for fn, url in imgs:
    try:
        data = requests.get(url, timeout=30).content
        open(os.path.join(base, fn), 'wb').write(data)
        print('OK', fn)
    except Exception as e:
        print('ERR', fn, e)
print('done')
