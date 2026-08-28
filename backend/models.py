from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from database import Base

class DkxxShpAttr(Base):
    __tablename__ = 'dkxx_shp_attrs'
    id = Column(Integer, primary_key=True, index=True)
    ysdm = Column(String)
    dkbm = Column(String, index=True, comment='地块编码')
    dkmc = Column(String, comment='地块名称')
    scmj = Column(Float, comment='实测面积')
    dkdz = Column(String, comment='地块东至')
    dkxz = Column(String, comment='地块西至')
    dknz = Column(String, comment='地块南至')
    dkbz = Column(String, comment='地块北至')
    # 其他字段可以自动通过 data_importer 构建在数据库表里，由于是动态的表，可在此按需映射核心字段用于API返回。
